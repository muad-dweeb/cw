import json
import os
import pickle
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, InvalidArgumentException, WebDriverException

from exceptions import ScraperException
from util import random_sleep


class ICScraper(object):

    def __init__(self, wait_range, time_limit=None, verbose=False):
        self.root = 'https://www.instantcheckmate.com/dashboard'
        self._driver = webdriver.Chrome()
        print('Chrome spawned at {}'.format(datetime.now()))

        self.last_contact_info = None
        # Seconds between searches, randomized to hopefully throw off bot-detection
        self._wait_range = wait_range
        self._time_limit = time_limit
        self._verbose = verbose

        # Internal metric
        self.reports_loaded = 0

        self._error_strings = {'404 Error': 'Uh Oh! Looks like something went wrong.',
                               '504 Error': 'we\'ve encountered an error.',
                               '500 Error': 'HTTP ERROR 500'}

    @staticmethod
    def _get_config(config_path):
        required_keys = {'email', 'pass'}
        config_path = os.path.expanduser(config_path)

        if not os.path.isfile(config_path):
            raise ScraperException('Config is not a valid file: {}'.format(config_path))

        try:
            with open(config_path, 'r') as f:
                config_dict = json.loads(f.read())
        except (OSError, ValueError) as e:
            raise ScraperException('Unable to load JSON from file: {}. Error: {}'.format(config_path, e))

        for key in required_keys:
            if key not in config_dict.keys():
                raise ScraperException('Config is missing required key: {}'.format(key))

        print('Config successfully loaded from: {}'.format(config_path))
        return config_dict

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

    def manual_login(self, cookie_file):
        """
        Just loads the login screen. It's up to the user to enter creds and click the stupid images
        :return:
        """
        login_url = self.root + '/login'
        try:
            self._load_page(login_url)
        except ScraperException as e:
            raise ScraperException('Unable to load login page: {}. {}'.format(login_url, e))

        if os.path.isfile(cookie_file):
            # Yeah, this definitely doesn't do anything useful...
            self.load_session_cookies(cookie_file)
            self._driver.refresh()

        # Verify login success
        success = False
        while not success:
            try:
                self._driver.find_element_by_id('report-history')
                success = True
            except NoSuchElementException:
                time.sleep(2)

        print('Login successful')
        self.save_session_cookies(cookie_file)

        return True

    def auto_login(self, config_path):
        """
        Without Re-Captcha circumvention, this method is not all that useful.
        It works, but all it really does is load the login page, input the creds,
          and then the user still needs to solve the bullshit to continue.
        :return:
        """
        # This needs to be a fair bit of time because these captchas are FUCKING IMPOSSIBLE TO SOLVE
        captcha_timeout = 360
        config = self._get_config(config_path=config_path)
        login_url = self.root + '/login'
        try:
            self._load_page(login_url)
        except ScraperException as e:
            raise ScraperException('Unable to load login page: {}. {}'.format(login_url, e))

        email_input = self._driver.find_element_by_css_selector("input[type='email']")
        pass_input = self._driver.find_element_by_css_selector("input[type='password']")

        email_input.send_keys(config['email'])
        pass_input.send_keys(config['pass'])
        pass_input.send_keys(Keys.RETURN)

        # MANUAL CAPTCHA RESOLUTION REQUIRED
        countdown_begin = time.time()
        print('You have {} seconds to clear all Captchas!'.format(captcha_timeout))

        # Verify login success
        success = False
        while not success:
            try:
                self._driver.find_element_by_id('report-history')
                success = True
            except NoSuchElementException:
                time.sleep(2)
            if time.time() - countdown_begin > captcha_timeout:
                raise ScraperException('Captcha not cleared in time')

        print('Login successful')

    def _detect_login_page(self):
        try:
            self._driver.find_element_by_css_selector("input[type='email']")
            self._driver.find_element_by_css_selector("input[type='password']")
        except NoSuchElementException:
            return False
        return True

    def find(self, first, last, city, state, verbose=False):
        matches = list()

        search_url = self.root + '/search/person/?first={}&last={}&city={}&state={}'.format(first, last, city, state)
        try:
            self._load_page(search_url)
        except ScraperException as e:
            raise ScraperException('Failed to load search page: {}. Error: {}'.format(search_url, e))

        while self._detect_login_page() and (self._time_limit is None or datetime.now() < self._time_limit):
            time.sleep(5)
        if self._detect_login_page():
            return ScraperException('Account logged out. Discontinuing scrape.')

        results_list = self._driver.find_elements_by_class_name('result')

        for result in results_list:
            found_first = result.get_attribute('data-first-name')
            found_last = result.get_attribute('data-last-name')
            found_full = result.get_attribute('data-full-name')
            found_city = result.get_attribute('data-location')
            found_age = result.get_attribute('data-age')

            # Basic validation against canonical search params
            if found_first.lower() != first.lower() or \
                    found_last.lower() != last.lower() or \
                    found_city.lower() != city.lower():
                continue

            # Secondary validation to make sure the most recent location matches the input city
            locations_list = result.find_elements_by_class_name('person-location')

            # No cities listed
            if len(locations_list) == 0:
                continue

            # First listed city does not match
            if locations_list[0].text.split(',')[0].lower() != city.lower():
                continue

            if verbose:
                print('Result: {}, Age: {}, City: {}'.format(found_full, found_age, found_city))

            # Only keep 100% input matches
            matches.append(result)

        # Free memory
        del results_list

        return matches

    def get_info(self, search_result):
        """
        Given a search, open its report and return the relevant information
        :param search_result: WebElement
        :return: dict
        """

        retry_wait_range = (0, 5)
        report_timeout = 180
        main_report = None
        contact_dict = {'phone_numbers': dict(), 'email_addresses': list()}

        # Big green button
        open_report = search_result.find_element_by_class_name('view-report')
        open_report.click()

        # Verify report generation success
        countdown_begin = time.time()
        success = False
        # TODO: dismiss tutorial overlay if it occurs
        while not success:
            try:
                main_report = self._driver.find_element_by_id('main-report')
                success = True

            # Simply waiting for the report to load...
            except NoSuchElementException:
                time.sleep(2)

            if time.time() - countdown_begin > report_timeout:

                # Loaded an error page instead of a report
                for error, message in self._error_strings.items():
                    if message in self._driver.page_source:

                        # Something is wrong with this particular report, probably server-side
                        if error == '500 Error':
                            print('Report broken; 500 Error detected.')

                            # Call it a loss and move on
                            return contact_dict

                        print('{} detected.'.format(error))
                        return error

                # Generic time-out
                else:
                    raise ScraperException('Report failed to generate in {} seconds'.format(report_timeout))

        print('Report load successful')
        self.reports_loaded += 1

        phone_rows = main_report.find_elements_by_class_name('phone-row')
        for row in phone_rows:
            phone_number = row.find_element_by_class_name('usage-phone-number').text
            try:
                phone_type = row.find_element_by_class_name('usage-line-type').text
            except NoSuchElementException:
                phone_type = 'unknown'

            # Skip fax numbers
            if phone_type.lower() == 'fax':
                continue

            contact_dict['phone_numbers'][phone_number] = phone_type

        email_rows = main_report.find_elements_by_class_name('email-usage')
        for row in email_rows:
            remove_button = row.find_element_by_class_name('remove')
            email_address = remove_button.get_attribute('data-source')
            contact_dict['email_addresses'].append(email_address)

        return contact_dict

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

            # Error page encountered; reload the search results page and try once more
            if type(single_info) == str and single_info in self._error_strings.keys():
                search_results = self.find(first=first, last=last, city=city, state=state)
                single_info = self.get_info(search_result=search_results[scrape_index])

            for number, number_type in single_info['phone_numbers'].items():
                full_info['phone_numbers'].add('{} ({})'.format(number, number_type))

            for value in single_info['email_addresses']:
                full_info['email_addresses'].add(value)

            if scrape_index > 0:
                random_sleep(self._wait_range, verbose=self._verbose)

            # Navigate back to search results page
            search_results = self.find(first=first, last=last, city=city, state=state)

            scrape_index += 1

        self.last_contact_info = full_info

        return full_info

    def close(self):
        self._driver.close()
        print('Chrome killed at {}'.format(datetime.now()))

