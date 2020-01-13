# -*- coding: utf-8 -*-

import atexit
import logging

from six.moves.urllib.parse import urlparse
from selenium.webdriver import ChromeOptions, Chrome, PhantomJS
from selenium.common.exceptions import WebDriverException

logger = logging.getLogger(__name__)


class BrowserHelper(type):
    def __new__(mcs, name, bases, dct):
        return super(BrowserHelper, mcs).__new__(mcs, name, bases, dct)


class HeadlessBrowser(object):
    def __init__(self):
        self.backend = ['chrome', 'phantomjs']
        self.driver = None
        atexit.register(self.cleanup)

    def __getattribute__(self, item):
        attr = object.__getattribute__(self, item)

        if hasattr(attr, '__call__'):
            func_name = attr.__name__

            if func_name in self.backend:
                def wrap_func(*args, **kwargs):
                    if self.driver is not None:
                        self.cleanup()

                    result = attr(*args, **kwargs)
                    return result
            else:
                def wrap_func(*args, **kwargs):
                    if self.driver is None:
                        logger.warning('Driver is NOT initialized, skip %s' % func_name)
                        return

                    result = attr(*args, **kwargs)
                    return result

            return wrap_func
        else:
            return attr

    def cleanup(self):
        if self.driver is not None:
            logger.info('CLEAN driver: %s' % self.driver)
            self.driver.quit()
            self.driver = None

    def chrome(self, chromedriver_path=None, disable_log=True, strip_ua4headless=True):
        """
        Better to place chromedriver and chrome/chromium binaries in the PATH,
            in this case, parameter chromedriver_path could be omitted and set as None
        Otherwise place them under the same directory and set parameter chromedriver_path
        ---------------------------------------------------------------------------------
        If chromedriver and chrome/chromium are in different path,
            beyond chromedriver_path setting, chrome/chromium path should be set as:
            options.binary_location = '/path'
        """
        options = ChromeOptions()
        options.add_argument('headless')
        options.add_argument('no-sandbox')

        if disable_log:
            options.add_argument('log-level=3')
            options.add_experimental_option('excludeSwitches', ['enable-logging'])

        try:
            if chromedriver_path:
                self.driver = Chrome(options=options,
                                     executable_path=chromedriver_path)
            else:
                self.driver = Chrome(options=options)
        except WebDriverException as e:
            logger.error(e.msg)
            self.driver = None
            return

        # self.driver.set_page_load_timeout(20)
        if strip_ua4headless:
            import re
            ua = re.sub('(?i)headless', '', self.ua())
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": ua})

    def phantomjs(self, exe_path=None, disable_log=True, log_path='logs/ghostdriver.log'):
        service_args = []
        if disable_log:
            service_args.append('--webdriver-loglevel=NONE')

        # I know phantomjs is deprecated, but I DO NOT LIKE the warnings...
        import warnings
        backup = warnings.warn
        warnings.warn = str

        try:
            if exe_path:
                self.driver = PhantomJS(executable_path=exe_path,
                                        service_args=service_args,
                                        service_log_path=log_path)
            else:
                self.driver = PhantomJS(service_args=service_args,
                                        service_log_path=log_path)
        except WebDriverException as e:
            logger.error(e.msg)
            self.driver = None
            return
        finally:
            warnings.warn = backup

    def get(self, url, report_html=False):
        if not urlparse(url).scheme:
            url = 'http://%s' % url

        self.driver.get(url)
        return self.driver.page_source if report_html else None

    def ua(self):
        return str(self.driver.execute_script("return navigator.userAgent"))

    def zoom(self, level=1):
        if isinstance(level, (int, float)):
            self.driver.execute_script("document.body.style.zoom = '%s'" % level)

    def capture(self, url, png_name=None, zoom_level=1):
        self.get(url)
        self.zoom(zoom_level)

        if png_name is None or not str(png_name).endswith('.png'):
            result = urlparse(url)
            if not result.scheme:
                result = urlparse('http://%s' % url)
                png_name = '%s.png' % result.netloc

        width = self.driver.execute_script(
            "return Math.max(document.body.scrollWidth, \
                             document.body.offsetWidth, \
                             document.documentElement.clientWidth, \
                             document.documentElement.scrollWidth, \
                             document.documentElement.offsetWidth);")

        height = self.driver.execute_script(
            "return Math.max(document.body.scrollHeight, \
                             document.body.offsetHeight, \
                             document.documentElement.clientHeight, \
                             document.documentElement.scrollHeight, \
                             document.documentElement.offsetHeight);")

        # resize
        self.driver.set_window_size(width, height)
        self.driver.save_screenshot(png_name)
