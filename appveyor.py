# -*- coding:utf-8 -*-

import json
import logging.config
import os
import sys
import yaml
from datetime import datetime
from pytz import timezone
import time
from collections import defaultdict

from checkinlibs.poro import Poro
from checkinlibs.banyungong import Banyungong
from browser import HeadlessBrowser

logging.config.dictConfig(yaml.load(open('logging.yaml', 'r'), Loader=yaml.FullLoader))
logger = logging.getLogger(__name__)

accounts_build = os.getenv('ACCOUNTS')
mark_file = 'accounts.txt'
site_conf = {
    'poro': {
        'cls': Poro,
        'cycle_hour': 24,
        'tz': 'Asia/Shanghai'
    },
    'banyungong': {
        'cls': Banyungong,
        'tz': 'Asia/Shanghai'
    },
}


def build_targets():
    """
    For appveyor hourly jobs, accounts are from system environment variable.
    Which can be encrypted and stored in appveyor configuration file.
    """
    global accounts_build
    if not accounts_build:
        logger.error('ENV accounts settings is EMPTY...')
        sys.exit(2)

    try:
        accounts_build = json.loads(accounts_build)
    except (BaseException, Exception):
        logger.error('Error parsing ENV accounts settings')
        sys.exit(3)

    results = defaultdict(dict)
    if os.path.isfile(mark_file):
        logger.debug('Reading last checking report from %s' % mark_file)
        try:
            results = json.load(open(mark_file, 'r'))
        except (BaseException, Exception):
            logger.info('Bad content in %s...' % mark_file)

    for site in accounts_build:
        if site not in site_conf:
            accounts_build[site] = None
            logger.debug('%s not in supported sites' % site)
            continue

        accounts_site = accounts_build[site]
        for seq in accounts_site:
            account = accounts_site[seq]
            account.update(site_conf[site])
            account['site'] = site
            account['seq'] = seq

            if site in results:
                result = results[site]
                if seq in result:
                    account.update(result[seq])


def gen_list():
    priority = []
    normal = []

    for site in site_conf:
        if site in accounts_build:
            timezone_site = timezone(site_conf[site]['tz'])
            accounts_site = accounts_build[site]
            for seq in accounts_site:
                account = accounts_site[seq]
                if not account['u'] or not account['p']:
                    logger.debug('DROP empty username or password...')
                    continue
                if 'timestamp' not in account:
                    account['timestamp'] = '1970-01-01 00:00:00'

                record = timezone_site.localize(datetime.strptime(account['timestamp'], '%Y-%m-%d %H:%M:%S'))
                if 'cycle_hour' in site_conf[site]:
                    current = int(time.time())
                    if int(record.timestamp()) + (account['cycle_hour'] * 3600) - 10 * 60 <= current:
                        account['plan'] = record.timestamp() + (account['cycle_hour'] * 3600)
                        priority.append(account)
                else:
                    current = datetime.utcnow().astimezone(timezone_site)
                    if record.year != current.year or record.month != current.month or record.day != current.day:
                        normal.append(account)

    priority.sort(key=lambda x: x['plan'])
    normal.sort(key=lambda x: x['seq'])
    return priority, normal


def checkin_job(browser, account):
    checkin_cls = account['cls'](browser.driver)
    username = account['u']
    password = account['p']
    if not username or not password:
        logger.warning('EMPTY username or password...')
        return False

    result = checkin_cls.checkin(username, password)
    if result is None:
        return False
    else:
        account['result'] = result[0]
        account['timestamp'] = result[1]
        return True


def do_checkin(browser, priority, normal, retry=False):
    priority_retry = []
    normal_retry = []
    normal_index = 0
    normal_length = len(normal)
    update_mark = False

    for working in priority:
        current = int(time.time())
        while working['plan'] > current:
            if normal_index < normal_length:
                if checkin_job(browser, normal[normal_index]):
                    update_mark = True
                else:
                    normal_retry.append(normal[normal_index])
                normal_index += 1
            else:
                waiting = working['plan'] - current
                logger.info('Priority job needs to wait for %s seconds' % waiting)
                time.sleep(waiting)
            current = int(time.time())

        if checkin_job(browser, working):
            update_mark = True
        else:
            priority_retry.append(working)

    while normal_index < normal_length:
        if checkin_job(browser, normal[normal_index]):
            update_mark = True
        else:
            normal_retry.append(normal[normal_index])
        normal_index += 1

    if retry:
        return update_mark
    elif priority_retry or normal_retry:
        if do_checkin(browser, priority_retry, normal_retry, retry=True):
            update_mark = True

    if update_mark:
        result_mark = defaultdict(dict)
        for site in accounts_build:
            result_mark[site] = defaultdict(dict)
            accounts_site = accounts_build[site]
            result_site = result_mark[site]

            for seq in accounts_site:
                account = accounts_site[seq]
                if 'timestamp' in account:
                    result_site[seq]['timestamp'] = account['timestamp']
                if 'result' in account:
                    result_site[seq]['result'] = account['result']

        with open(mark_file, 'w') as f:
            json.dump(result_mark, f, sort_keys=True, indent=4)


def main():
    build_targets()
    priority, normal = gen_list()

    browser = HeadlessBrowser()
    browser.chrome()
    do_checkin(browser, priority, normal)


if __name__ == '__main__':
    main()
