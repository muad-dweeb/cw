import pickle
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import InvalidArgumentException, WebDriverException

from exceptions import ScraperException
from scrape.util import random_sleep


class Scraper(object):

    def __init__(self, wait_range, time_limit=None, verbose=False):
        self._driver = webdriver.Chrome()
        print('Chrome spawned at {}'.format(datetime.now()))

        self.last_contact_info = None
        # Seconds between searches, randomized to hopefully throw off bot-detection
        self._wait_range = wait_range
        self._time_limit = time_limit
        self._verbose = verbose

        # Internal metric
        self.reports_loaded = 0

        # This needs to be implemented in the derived class, as the values will be unique to each site
        self._error_strings = dict()

    def save_session_cookies(self, file_path):
        pickle.dump(self._driver.get_cookies(), open(file_path, 'wb'))
        if self._verbose:
            print('Session cookies saved to: {}'.format(file_path))

    def load_session_cookies(self, file_path):
        for cookie in pickle.load(open(file_path, 'rb')):
            for key, value in cookie.items():
                value = str(value)
                try:
                    self._driver.add_cookie({'name': key, 'value': value})
                except InvalidArgumentException as e:
                    raise ScraperException('Failed to add cookie key \'{}\' to session. Error: {}'.format(key, e))
        if self._verbose:
            print('Session cookies loaded from: {}'.format(file_path))

    def _load_page(self, url, retry=3):
        success = False
        retry_wait_range = (0, 10)
        while success is False and retry > 0:
            try:
                self._driver.get(url)
                for error, message in self._error_strings.items():
                    if message in self._driver.page_source:
                        print('{} detected.'.format(error))
                        random_sleep(retry_wait_range, verbose=True)
                else:
                    success = True
            except WebDriverException as e:
                retry -= 1
                print('{}. Retries left: {}'.format(e, retry))
        if success is False:
            raise ScraperException('Page failed to load; retry limit reached.')

    def close(self):
        self._driver.close()
        print('Chrome killed at {}'.format(datetime.now()))
