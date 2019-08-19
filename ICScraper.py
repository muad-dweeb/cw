import json
import os
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, NoSuchWindowException

from exceptions import ScraperException


class ICScraper(object):

    def __init__(self, config_path):
        self.root = 'https://www.instantcheckmate.com/dashboard'
        self._config = self._get_config(config_path=config_path)

        self._driver = webdriver.Chrome()
        print('Chrome spawned at {}'.format(datetime.now()))

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

    def login(self):
        captcha_timeout = 120
        login_url = self.root + '/login'
        self._driver.get(login_url)

        email_input = self._driver.find_element_by_css_selector("input[type='email']")
        pass_input = self._driver.find_element_by_css_selector("input[type='password']")

        email_input.send_keys(self._config['email'])
        pass_input.send_keys(self._config['pass'])
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

    def find(self, first, last, city, state):
        matches = list()

        search_url = self.root + '/search/person/?first={}&last={}&city={}&state={}'.format(first, last, city, state)
        self._driver.get(search_url)

        results_list = self._driver.find_elements_by_class_name('result')

        for result in results_list:
            found_first = result.get_attribute('data-first-name')
            found_last = result.get_attribute('data-last-name')
            found_city = result.get_attribute('data-location')

            # Basic validation against canonical search params
            if found_first.lower() != first.lower() or \
                    found_last.lower() != last.lower() or \
                    found_city.lower() != city.lower():
                continue

            # Secondary validation to make sure the most recent location matches the input city
            locations_list = result.find_elements_by_class_name('person-location')
            if locations_list[0].split(',')[0].lower() != city.lower():
                continue

            # Only keep 100% input matches
            matches.append(result)

        # Free memory
        del results_list

        print('{} matching results found.'.format(len(matches)))
        return matches

    def get_info(self, search_result):
        """
        Given a search, open their reports and return the relevant information
        :param search_result: WebElement
        :return:
        """

        report_timeout = 180
        main_report = None
        contact_info = {'phone_numbers': dict(), 'email_address': list()}

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
            except NoSuchElementException:
                time.sleep(2)
            if time.time() - countdown_begin > report_timeout:
                raise ScraperException('Report failed to generate in {} seconds'.format(report_timeout))

        print('Report load successful')

        phone_rows = main_report.find_elements_by_class_name('phone-row')
        for row in phone_rows:
            phone_number = row.find_element_by_class_name('usage-phone-number').text
            phone_type = row.find_element_by_class_name('usage-line-type').text
            contact_info['phone_numbers'][phone_number] = phone_type

        email_rows = main_report.find_elements_by_class_name('email-usage')
        for row in email_rows:
            remove_button = row.find_element_by_class_name('remove')
            email_address = remove_button.get_attribute('data-source')
            contact_info['email_addresses'].append(email_address)

        return contact_info

    def close(self):
        self._driver.close()
        print('Chrome killed at {}'.format(datetime.now()))


if __name__ == '__main__':
    scraper = None
    try:
        scraper = ICScraper('~/muad-dweeb/cw/config/ic_creds.json')  # TODO: remove hardcoded path
        # TODO: Maybe login should just be a fully manual process... no creds file involved?
        scraper.login()

        matches = scraper.find('andrew', 'galloway', 'seattle', 'wa')

        # TESTING
        first_match = matches[0]
        contact_info = scraper.get_info(first_match)
        # TODO: figure out how to loop all matches. Probably need to rerun the search and checkpoint the matches?

    except ScraperException as e:
        print('Scrape failed. Error: {}'.format(e))

    except NoSuchWindowException:
        print('Window was closed prematurely')

    if scraper:
        scraper.close()
