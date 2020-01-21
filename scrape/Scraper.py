import pickle
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import InvalidArgumentException, WebDriverException

from lib.exceptions import ScraperException
from scrape.TorProxy import check_ip, TorProxy
from scrape.util import random_sleep


class Scraper(object):

    def __init__(self, wait_range, time_limit=None, use_proxy=False, verbose=False):

        self._driver = webdriver.Chrome()
        print('Chrome spawned at {}'.format(datetime.now()))

        self.ip = check_ip(self._driver)
        print('Your IP: {}'.format(self.ip))

        self._use_proxy = use_proxy
        if use_proxy:
            self._driver = self._spawn_driver_with_proxy()

        self.last_contact_info = None
        # Seconds between searches, randomized to hopefully throw off bot-detection
        self._wait_range = wait_range
        self._time_limit = time_limit
        self._verbose = verbose

        # Internal metric
        self.reports_loaded = 0

        # Most error messages will be specific to individual sites. Add those in each derived class
        self._error_strings = {'1020 Error': 'used Cloudflare to restrict access'}

    def _spawn_driver_with_proxy(self):
        proxy = TorProxy()
        proxy.start()
        proxy_driver = webdriver.Chrome(desired_capabilities=proxy.capabilities)

        proxy_ip = check_ip(proxy_driver)

        print('Securing TOR proxy: {} --> {}'.format(self.ip, proxy_ip))

        # Close the non-proxied browser
        self._driver.close()

        if self.ip == proxy_ip:
            raise ScraperException('Failed to secure a proxy IP address')
        else:
            self.ip = proxy_ip

        return proxy_driver

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

                        # Cloudflare or site bot detection; reload driver/proxy and try again
                        if error in ('1020 Error', 'Bot Check') and self._use_proxy:
                            print('Spawning fresh driver with proxy')
                            self._driver = self._spawn_driver_with_proxy()
                            break

                        # Any other error type, wait a bit and try without reloading driver
                        else:
                            random_sleep(retry_wait_range, verbose=True)
                else:
                    success = True
            except WebDriverException as e:
                retry -= 1
                print('{}. Retries left: {}'.format(e, retry))
        if success is False:
            raise ScraperException('Page failed to load; retry limit reached.')

    def find(self, first, last, city, state, verbose):
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

        search_results = self.find(first=first, last=last, city=city, state=state, verbose=True)
        print('{} matching results found.'.format(len(search_results)))

        # NOTE: New elements are generated each time the search page is loaded, rendering all previous elements stale
        while scrape_index < len(search_results):

            # Opens Report and generates info dict
            single_info = self.get_info(search_result=search_results[scrape_index])

            if type(single_info) == str and single_info in self._error_strings.keys():

                # Error page encountered; reload the search results page and try once more
                search_results = self.find(first=first, last=last, city=city, state=state, verbose=False)
                single_info = self.get_info(search_result=search_results[scrape_index])

            for number, number_type in single_info['phone_numbers'].items():
                full_info['phone_numbers'].add('{} ({})'.format(number, number_type))

            for value in single_info['email_addresses']:
                full_info['email_addresses'].add(value)

            # Don't wait after the last report; there will be a wait when the next row starts
            if scrape_index == 0 or scrape_index < len(search_results) - 1:

                # It takes a human some time to do anything with the report's information
                random_sleep(self._wait_range, verbose=self._verbose)

            # Navigate back to search results page (and reload elements)
            search_results = self.find(first=first, last=last, city=city, state=state, verbose=False)

            scrape_index += 1

        self.last_contact_info = full_info

        return full_info

    def close(self):
        self._driver.close()
        print('Chrome killed at {}'.format(datetime.now()))
