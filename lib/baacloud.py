# -*- coding: utf-8 -*-

import json
import logging

import lxml.html

from curl import LoginRequest

logger = logging.getLogger(__name__)


class BaaCloudRequest(LoginRequest):
    def __init__(self):
        LoginRequest.__init__(self)

        self.tag = '[**baacloud**]'
        self.login_url = 'https://www.baacloud.net/modules/_login.php'
        self.precheck_url = 'https://www.baacloud.net/modules/index.php'
        self.checkin_url = 'http://www.baacloud.net/modules/_checkin.php'
        self.logout_url = 'https://www.baacloud.net/modules/logout.php'

    def login(self, account, password):
        """
        :param account  - User account
        :param password - User password
        :return:
            None    - login successful with no error
            bla bla - login failed reason
        """

        ret = u'Login Failed'

        postdata = {'email': account, 'passwd': password, 'remember_me': 'week'}
        resp = self.fetch(self.login_url, method='POST', data=postdata)

        if self.result.get('code') == 200:
            index = resp.find('{')
            if index > 0:
                try:
                    resp = json.loads(resp[index:])
                    if resp.get('code') == u'1' and resp.get('msg') == u'欢迎回来':
                        ret = None
                        logger.info('[baacloud] Successfully login for %s' % account)
                except ValueError:
                    pass

        return ret

    def logout(self):
        """
        If we have session cookie, call logout to fresh cookies.
        Seems we can clean cookie instead...
        """
        if self.cookie is not None:
            self.fetch(self.logout_url)

    def checkin(self, str_cookie=None):
        """
        :param str_cookie - Stored Cookie for web access w/o account and password
        :return:
            None        - failed to checkin, possible for cookie expired
                          if the site changed the checkin API, this may None as well
            str of days - already checkin days returned by site
        """
        amount = None

        if str_cookie is not None:
            logger.debug('[baacloud] Using strcookie: %s', str_cookie)
            self.load_cookie(str_cookie)

        resp = self.fetch(self.precheck_url)
        dom = lxml.html.fromstring(resp)
        pre_check = dom.xpath('//button[@id="checkin"]')
        if len(pre_check) > 0:
            check_button = pre_check[0].text.strip()
            if check_button == u'签到':
                resp = self.fetch(self.checkin_url, method='POST',
                                  header={'Content-Type': None})
                if self.result.get('code') == 200:
                    index = resp.find('{')
                    if index > 0:
                        try:
                            resp = json.loads(resp[index:])
                            amount = resp.get('msg')
                            logger.info('[baacloud] Credit: ' + amount)
                        except ValueError:
                            logger.error('[baacloud] Checkin result is NOT json format...')
                    else:
                        logger.error('[baacloud] Checkin result is NOT json format...')
                else:
                    logger.error('[baacloud] Checkin POST request failed...')
            elif check_button == u'不能签到':
                logger.info('[baacloud] Already checked in...')
            else:
                logger.error('[baacloud] Unknown button text: ' + check_button)
        else:
            logger.error('[baccloud] No checkin button...')

        return amount
