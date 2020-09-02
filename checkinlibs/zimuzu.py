# -*- coding: utf-8 -*-

import logging
import re

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

from . import SeleniumRequest

logger = logging.getLogger(__name__)


class Zimuzu(SeleniumRequest):
    def checkin(self, username, password):
        logger.info('%s: check account %s...' % (self.__class__.__name__, username))

        self.driver.get("http://zimuzu.tv")
        try:
            refresh_timeout = 10
            WebDriverWait(self.driver, refresh_timeout).until(
                EC.presence_of_element_located((By.LINK_TEXT, u"登入")))
            self.driver.find_element(By.LINK_TEXT, u"登入").click()
            self.driver.find_element(By.NAME, "email").send_keys(username)
            self.driver.find_element(By.NAME, "password").send_keys(password)
            self.driver.find_element(By.NAME, "password").send_keys(Keys.ENTER)

            logger.debug('%s: waiting for account appearing...', self.__class__.__name__)
            refresh_timeout = 30
            WebDriverWait(self.driver, refresh_timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".av")))
            self.driver.find_element(By.CSS_SELECTOR, ".av").click()

            report = self.driver.find_element(By.CSS_SELECTOR, '.data-summary').text
            pattern = re.compile(u'最后登录' + r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
            timestamp = re.findall(pattern, report)
            if timestamp:
                timestamp = timestamp[0]
                logger.debug('%s: %s Last login at %s' % (self.__class__.__name__, username, timestamp))

                report = self.driver.find_element(By.CSS_SELECTOR, '.u_acount_a1').text
                pattern = re.compile(u'人人钻[^\d]*' + r'(\d+)')
                bonus = re.findall(pattern, report)
                if bonus:
                    bonus = bonus[0]
                    logger.debug('%s: %s now has %s points' % (self.__class__.__name__, username, bonus))

                return bonus, timestamp
            else:
                return None
        except NoSuchElementException as e:
            logger.warning('%s: Unable do checkin for %s' % (self.__class__.__name__, username))
            logger.warning(e.msg)
            return None
        except TimeoutException:
            logger.warning(u'%s: may need to enlarge the waiting time, current value is %s' %
                           (self.__class__.__name__, refresh_timeout))
            logger.debug(self.driver.page_source)
            return None
