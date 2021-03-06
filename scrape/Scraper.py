import pickle
import random
import time
from datetime import datetime
from os import path

from selenium import webdriver
from selenium.common.exceptions import InvalidArgumentException, WebDriverException

from lib.exceptions import ScraperException
from scrape.TorProxy import check_ip, TorProxy


class Scraper(object):

    def __init__(self, logger, wait_range, chromedriver_path, time_limit=None, use_proxy=False, limit_info_grabs=42):

        self.logger = logger

        self._driver = webdriver.Chrome(executable_path=chromedriver_path)
        self.logger.debug('Chrome spawned at {}'.format(datetime.now()))

        self.ip = check_ip(self._driver)
        self.logger.debug('Your IP: {}'.format(self.ip))

        self._use_proxy = use_proxy
        if use_proxy:
            self._driver = self._spawn_driver_with_proxy()

        self.last_contact_info = None

        # Seconds between searches, randomized to hopefully throw off bot-detection
        self._wait_range = wait_range

        # Time to halt execution
        self._time_limit = time_limit

        # Maximum number of emails or phone numbers to grab per search
        self._limit_info_grabs = limit_info_grabs

        # Internal metric
        self.reports_loaded = 0

        # Most error messages will be specific to individual sites. Add those in each derived class
        self._error_strings = {'1020 Error': 'used Cloudflare to restrict access'}

    def _spawn_driver_with_proxy(self):
        proxy = TorProxy()
        proxy.start()
        proxy_driver = webdriver.Chrome(desired_capabilities=proxy.capabilities)

        proxy_ip = check_ip(proxy_driver)

        self.logger.debug('Securing TOR proxy: {} --> {}'.format(self.ip, proxy_ip))

        # Close the non-proxied browser
        self._driver.close()

        if self.ip == proxy_ip:
            raise ScraperException('Failed to secure a proxy IP address')
        else:
            self.ip = proxy_ip

        return proxy_driver

    def save_session_cookies(self, file_path):
        pickle.dump(self._driver.get_cookies(), open(file_path, 'wb'))
        self.logger.debug('Session cookies saved to: {}'.format(file_path))

    def load_session_cookies(self, file_path):
        if path.isfile(file_path):
            for cookie in pickle.load(open(file_path, 'rb')):
                for key, value in cookie.items():
                    value = str(value)
                    try:
                        self._driver.add_cookie({'name': key, 'value': value})
                    except InvalidArgumentException as e:
                        raise ScraperException('Failed to add cookie key \'{}\' to session. Error: {}'.format(key, e))
            self.logger.debug('Session cookies loaded from: {}'.format(file_path))
        else:
            self.logger.debug('No cookies found at: {}'.format(file_path))

    def _load_page(self, url, retry=3):
        success = False
        retry_wait_range = (0, 10)
        while success is False and retry > 0:
            try:
                self._driver.get(url)
                for error, message in self._error_strings.items():
                    if message in self._driver.page_source:
                        self.logger.error('{} detected.'.format(error))

                        # Cloudflare or site bot detection; reload driver/proxy and try again
                        if error in ('1020 Error', 'Bot Check') and self._use_proxy:
                            self.logger.debug('Spawning fresh driver with proxy')
                            self._driver = self._spawn_driver_with_proxy()
                            break

                        # Any other error type, wait a bit and try without reloading driver
                        else:
                            self.random_sleep(retry_wait_range)
                else:
                    success = True
            except WebDriverException as e:
                retry -= 1
                self.logger.error('{}. Retries left: {}'.format(e, retry))
        if success is False:
            raise ScraperException('Page failed to load; retry limit reached.')

    def find(self, first, last, city, state):
        raise NotImplementedError('Implement me in derived class, sucka')

    def get_info(self, search_result):
        raise NotImplementedError('Implement me in derived class, punk')

    def get_all_info(self, first, last, city, state):
        """
        Wrapper for find() and get_info() if all results are desirable. De-duping built-in.
        :return: dict
        """
        full_info = {'phone_numbers': set(), 'email_addresses': set()}
        scrape_index = 0

        search_results = self.find(first=first, last=last, city=city, state=state)
        self.logger.debug('{} matching results found.'.format(len(search_results)))

        # NOTE: New elements are generated each time the search page is loaded, rendering all previous elements stale
        while scrape_index < len(search_results) and \
                len(full_info['phone_numbers']) < self._limit_info_grabs and \
                len(full_info['email_addresses']) < self._limit_info_grabs:

            # Opens Report and generates info dict
            single_info = self.get_info(search_result=search_results[scrape_index])

            if type(single_info) == str and single_info in self._error_strings.keys():

                # Error page encountered; reload the search results page and try once more
                search_results = self.find(first=first, last=last, city=city, state=state)
                single_info = self.get_info(search_result=search_results[scrape_index])

            for number, number_type in single_info['phone_numbers'].items():
                full_info['phone_numbers'].add(number)

            for value in single_info['email_addresses']:
                full_info['email_addresses'].add(value)

            # Don't wait after the last report; there will be a wait when the next row starts
            if scrape_index == 0 or scrape_index < len(search_results) - 1:

                # It takes a human some time to do anything with the report's information
                self.random_sleep(self._wait_range)

            # Navigate back to search results page (and reload elements)
            search_results = self.find(first=first, last=last, city=city, state=state)

            scrape_index += 1

        if len(full_info['phone_numbers']) >= self._limit_info_grabs:
            self.logger.info('Phone numbers grabbed exceeds defined limit of {}, '
                             'moving on to next search.'.format(self._limit_info_grabs))

        if len(full_info['email_addresses']) >= self._limit_info_grabs:
            self.logger.info('Email addresses grabbed exceeds defined limit of {}, '
                             'moving on to next search.'.format(self._limit_info_grabs))

        self.last_contact_info = full_info

        return full_info

    def close(self):
        self._driver.close()
        self.logger.info('Chrome killed at {}'.format(datetime.now()))

    def random_sleep(self, range_tuple):
        wait_time = random.uniform(*range_tuple)
        self.logger.debug('Waiting for {} seconds...'.format(round(wait_time, 2)))
        time.sleep(wait_time)

    def save_screenshot(self):
        """
        Save a PNG capture of the current window
        """
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = path.join('/tmp', '.{}_screenshot.png'.format(now))
        self._driver.save_screenshot(output_file)
        self.logger.debug('Screenshot saved to: {}'.format(output_file))
        return output_file
