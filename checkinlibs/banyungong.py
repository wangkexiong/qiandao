# -*- coding: utf-8 -*-

from datetime import datetime
import logging

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from . import SeleniumRequest

logger = logging.getLogger(__name__)


class Banyungong(SeleniumRequest):
    def checkin(self, username, password):
        logger.info('%s: check account %s...' % (self.__class__.__name__, username))

        self.driver.get("http://banyungong.org")
        try:
            self.driver.find_element(By.ID, "ucHeader1_txtID").send_keys(username)
            self.driver.find_element(By.ID, "ucHeader1_txtPass").send_keys(password)
            self.driver.find_element(By.ID, "ucHeader1_ckbAutoLogin").click()
            self.driver.find_element(By.ID, "ucHeader1_btnLogin").click()
            self.driver.find_element(By.ID, "ucHeader1_hlkDaySign").click()
        except NoSuchElementException:
            logger.warning('%s: Unable do checkin for %s' % (self.__class__.__name__, username))
            logger.debug(self.driver.page_source)
            return None

        if u'今日已签到' not in self.driver.page_source:
            try:
                self.driver.find_element(By.ID, "btnSign").click()
            except NoSuchElementException:
                logger.warning('%s: login button not found...')
                return None

        bonus = self.driver.find_element(By.ID, "lblSignDay").text
        timestamp = self.driver.find_element(By.ID, "lblLastSignTime").text
        timestamp = timestamp.replace('/', '-')
        logger.debug('%s: login at %s and report day %s' % (self.__class__.__name__, timestamp, bonus))

        return bonus, timestamp
