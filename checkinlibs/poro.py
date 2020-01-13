# -*- coding: utf-8 -*-

import logging
import re

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from . import SeleniumRequest

logger = logging.getLogger(__name__)


class Poro(SeleniumRequest):
    def checkin(self, username, password):
        ajax_timeout = 10
        logger.info('%s: check account %s...' % (self.__class__.__name__, username))

        self.driver.get("http://poro.cx")
        try:
            self.driver.find_element(By.ID, "email").send_keys(username)
            self.driver.find_element(By.ID, "passwd").send_keys(password)
            self.driver.find_element(By.ID, "remember_me").click()
            self.driver.find_element(By.ID, "login").click()

            button = WebDriverWait(self.driver, ajax_timeout).until(
                EC.presence_of_element_located((By.ID, "checkin")))
        except NoSuchElementException:
            logger.warning('%s: Unable to login' % self.__class__.__name__)
            logger.debug(self.driver.page_source)
            return None
        except TimeoutException:
            logger.warning('%s: %s log in failed...' % (self.__class__.__name__, username))
            return None

        bonus = None
        text = button.text.strip()
        if text == u"点击签到":
            button.click()
            try:
                WebDriverWait(self.driver, ajax_timeout).until(
                    EC.text_to_be_present_in_element((By.ID, "checkin-msg"), u'获得'))
            except TimeoutException:
                logger.warning('%s: %s checked in but failed to get detail response...' %
                               (self.__class__.__name__, username))
            else:
                msg = self.driver.find_element(By.ID, "checkin-msg").text
                match = re.search('\\d+', msg)
                if match:
                    bonus = match.group()
                logger.info('%s: %s gained %s' % (self.__class__.__name__, username, bonus))

        self.driver.execute_script("location.reload()")
        resp = self.driver.find_element(By.CSS_SELECTOR, ".col-xs-8 > span").text
        logger.debug(' '.join(resp.splitlines()))

        match = re.search('\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}', resp)
        if match:
            text = match.group()
            timestamp = text
            logger.debug('%s: %s checked in at %s' % (self.__class__.__name__, username, timestamp))
        else:
            # We DO NOT care timezone offset in this case...
            timestamp = '1970-01-01 00:00:00'
            logger.debug('%s: No time provided for %s' % (self.__class__.__name__, username))

        return bonus, timestamp
