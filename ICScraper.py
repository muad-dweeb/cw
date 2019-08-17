import json
import os
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

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
        search_url = self.root + '/search/person/?first={}&last={}&city={}&state={}'.format(first, last, city, state)
        self._driver.get(search_url)

    def close(self):
        self._driver.close()
        print('Chrome killed at {}'.format(datetime.now()))


if __name__ == '__main__':
    scraper = None
    try:
        scraper = ICScraper('~/muad-dweeb/cw/config/ic_creds.json')  # TODO: remove hardcoded path
        # TODO: Maybe login should just be a fully manual process... no creds file involved?
        scraper.login()
    except ScraperException as e:
        print('Scrape failed. Error: {}'.format(e))
    if scraper:
        scraper.close()
