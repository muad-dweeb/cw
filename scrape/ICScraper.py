import os
import time
from datetime import datetime

from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

from lib.exceptions import ScraperException
from scrape.Scraper import Scraper
from scrape.util import get_config


class ICScraper(Scraper):

    def __init__(self, logger, wait_range, chromedriver_path, time_limit=None, use_proxy=False):
        super().__init__(logger, wait_range, chromedriver_path, time_limit, use_proxy)
        self.root = 'https://www.instantcheckmate.com/dashboard'

        site_specific_error_strings = {'404 Error': 'Uh Oh! Looks like something went wrong.',
                                       '504 Error': 'we\'ve encountered an error.',
                                       '500 Error': 'HTTP ERROR 500',
                                       '502 Error': 'The web server reported a bad gateway error.'}

        # Add to the base class error dict
        for key, value in site_specific_error_strings.items():
            self._error_strings[key] = value

    def login(self, cookie_file):
        return self.manual_login(cookie_file)

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

        self.logger.info('Login successful')
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
        config = get_config(config_path=config_path)
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
        self.logger.warning('You have {} seconds to clear all Captchas!'.format(captcha_timeout))

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

        self.logger.info('Login successful')

    def _detect_login_page(self):
        try:
            self._driver.find_element_by_css_selector("input[type='email']")
            self._driver.find_element_by_css_selector("input[type='password']")
        except NoSuchElementException:
            return False
        return True

    def _detect_captcha(self):
        """
        What can I do to prevent this in the future?

        If you are on a personal connection, like at home, you can run
        an anti-virus scan on your device to make sure it is not infected with malware.

        If you are at an office or shared network, you can ask the network administrator to run a scan across the
        network looking for misconfigured or infected devices.

        Another way to prevent getting this page in the future is to use Privacy Pass. You may need to download
        version 2.0 now from the Chrome Web Store.
        """
        try:
            # Alternative search:  <form class="challenge-form" id="challenge-form"
            self._driver.find_element_by_id('recaptcha_widget')
        except NoSuchElementException:
            return False
        return True

    def find(self, first, last, city, state):
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

        while self._detect_captcha() and (self._time_limit is None or datetime.now() < self._time_limit):
            time.sleep(5)
        if self._detect_captcha():
            return ScraperException('Captcha detected. Discontinuing scrape.')

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

            self.logger.info('Result: {}, Age: {}, City: {}'.format(found_full, found_age, found_city))

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

        report_timeout = 180
        main_report = None
        contact_dict = {'phone_numbers': dict(), 'email_addresses': list()}

        self._click_the_button(search_result)

        if self._detect_login_page():
            return ScraperException('Account logged out. Discontinuing scrape.')

        if self._detect_captcha():
            return ScraperException('Captcha detected. Discontinuing scrape.')

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
                self.logger.error('Unable to find report. Sleeping for 2 seconds.')
                time.sleep(2)
                self._click_the_button(search_result)

            # Loaded an error page instead of a report
            for error, message in self._error_strings.items():
                if message in self._driver.page_source:

                    # Something is wrong with this particular report, probably server-side
                    if error == '500 Error':
                        self.logger.error('Report broken; 500 Error detected.')

                        # Call it a loss and move on
                        return contact_dict

                    self.logger.error('{} detected.'.format(error))
                    return error

            # Generic time-out
            if time.time() - countdown_begin > report_timeout:
                raise ScraperException('Report failed to generate in {} seconds'.format(report_timeout))

        self.logger.info('Report load successful')
        self.reports_loaded += 1

        phone_rows = main_report.find_elements_by_class_name('phone-row')
        for row in phone_rows:
            phone_number = row.find_element_by_class_name('usage-phone-number').text
            try:
                phone_type = row.find_element_by_class_name('usage-line-type').text
            except NoSuchElementException:
                phone_type = 'unknown'

            # Skip undesirable numbers
            if phone_type.lower() in ('fax', 'voip', 'landline', 'unknown'):
                continue

            contact_dict['phone_numbers'][phone_number] = phone_type

        email_rows = main_report.find_elements_by_class_name('email-usage')
        for row in email_rows:
            remove_button = row.find_element_by_class_name('remove')
            email_address = remove_button.get_attribute('data-source')
            contact_dict['email_addresses'].append(email_address)

        return contact_dict

    @staticmethod
    def _click_the_button(search_result):
        # Big green button
        time.sleep(5)
        open_report_button = search_result.find_element_by_class_name('view-report')
        open_report_button.click()
