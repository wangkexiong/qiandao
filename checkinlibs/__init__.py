# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger(__name__)


class SeleniumRequest(object):
    def __init__(self, driver):
        self.driver = driver
        if self.driver is not None:
            self.driver.delete_all_cookies()

    def checkin(self, username, password):
        pass
