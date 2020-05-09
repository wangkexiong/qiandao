# -*- coding:utf-8 -*-

import Queue
import datetime
import json
import logging.config
import os
import re
import time
from functools import wraps
from threading import Thread

import schedule
import yaml
from concurrent.futures import ThreadPoolExecutor, wait

from lib import XiamiRequest, BanyungongRequest, PoroRequest, BaaCloudRequest

logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=100)
result_Q = Queue.Queue()

site_conf = {
    'xiami': {
        'env': 'XIAMI_ACCOUNTS',
        'cls': XiamiRequest,
        'tz': 8,
    },
    'banyungong': {
        'env': 'BANYUNGONG_ACCOUNTS',
        'cls': BanyungongRequest,
        'tz': 8,
    },
    'poro': {
        'env': 'PORO_ACCOUNTS',
        'cls': PoroRequest,
        'cycle_hour': 24,
    },
    'baacloud': {
        'env': 'BAACLOUD_ACCOUNTS',
        'cls': BaaCloudRequest,
        'cycle_hour': 24,
    },
}


def memoize(func):
    memo = {}

    @wraps(func)
    def wrapper(*args):
        if args in memo:
            logger.debug('Fetch from cache for %s(%s)' % (
                func.func_name, ','.join(["'" + x + "'" if type(x) is str else str(x) for x in args])))
            return memo[args]
        else:
            rv = func(*args)
            memo[args] = rv
            return rv

    return wrapper


@memoize
def check_status_2json(site):
    checked = dict()
    checked_file = site + '.txt'

    if os.path.isfile(checked_file):
        logger.debug('Reading last checking report from %s' % checked_file)
        try:
            checked = json.load(open(checked_file, 'r'))
        except Exception as e:
            logger.info('Bad content in %s...' % checked_file)
            checked = dict()

    return checked


def checkin_job(site):
    futures_list = []
    if site not in site_conf:
        return futures_list

    env_var = site_conf[site]['env']
    env_users = os.getenv(env_var)
    if env_users is None:
        logger.info('NO %s is set', env_var)
        return futures_list

    try:
        users = json.loads(env_users)
    except Exception as e:
        logger.exception('Error parsing %s settings', env_var)
        return futures_list

    for seq, account in users.items():
        user_info = dict()
        user_info['seq'] = seq
        user_info['u'] = account.get('u', None)
        user_info['p'] = account.get('p', None)
        futures_list.append(executor.submit(do_checkin, site, user_info))

    return futures_list


def do_checkin(site, user_info):
    seq = user_info['seq']
    u = user_info['u']
    p = user_info['p']
    checkin_cls = site_conf[site]['cls']

    if u is None:
        return

    checked = check_status_2json(site)
    skip = True
    pre_sleep = 0

    if seq not in checked:
        skip = False
    else:
        logger.info(
            '[%s] %s last checkin at %s' % (
                site, u, str(datetime.datetime.utcfromtimestamp(checked[seq]['timestamp']))))
        current = int(time.time())

        if 'tz' in site_conf[site]:
            tz = site_conf[site]['tz']
            site_new_day = (((current + tz * 3600) / 86400) * 86400) - tz * 3600
            if checked[seq]['timestamp'] < site_new_day:
                skip = False
        elif 'cycle_hour' in site_conf[site]:
            cycle_round = site_conf[site]['cycle_hour']
            delta = current - checked[seq]['timestamp']

            if delta >= cycle_round * 3600:
                skip = False
            elif delta >= int((cycle_round - 0.75) * 3600):
                site_next_hour = current / 3600 * 3600 + 3600
                if 'half_zone' in site_conf[site]:
                    site_next_hour += (site_conf[site]['half_zone'] * 3600)
                if site_next_hour > (checked[seq]['timestamp'] + 24 * 3600):
                    pre_sleep = 24 * 3600 - delta
                    skip = False

    if not skip:
        if pre_sleep > 0:
            logger.info('[%s] %s wait for %s seconds...' % (site, u, pre_sleep))
            time.sleep(pre_sleep + 1)

        kls = checkin_cls()
        if not kls.login(u, p):
            result = kls.checkin()
            if result:
                result = '/'.join(re.findall('\\d+', result))
                result_Q.put((site, seq, result, int(time.time())))
    else:
        logger.info('[%s] %s already checked in ...' % (site, u))


def main():
    futures = []
    checked = {}
    updated = {}

    for site in site_conf:
        checked[site] = check_status_2json(site)
        futures.extend(checkin_job(site))
    wait(futures)

    for x in xrange(result_Q.qsize()):
        (site, seq, result, timestamp) = result_Q.get()
        if seq not in checked:
            checked[site][seq] = dict()

        checked[site][seq]['result'] = result
        checked[site][seq]['timestamp'] = timestamp
        updated[site] = True

    for site in site_conf:
        if site in updated and updated[site]:
            checked_file = site + '.txt'
            f = open('update.flag', 'a')
            f.write(checked_file + '\n')
            f.close()
            json.dump(checked[site], open(checked_file, 'w'))


def show_time(duration):
    logger.info('waiting another %s...' % duration)


def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    logging.config.dictConfig(yaml.load(open('logging.yaml', 'r')))

    schedule.every(10).minutes.do(show_time, '10 minutes')
    t = Thread(target=run_schedule)
    t.setDaemon(True)
    t.start()

    main()
