import os
import time

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys

from lib.exceptions import ScraperException
from scrape.Scraper import Scraper
from scrape.util import get_config


class BVScraper(Scraper):

    def __init__(self, wait_range, chromedriver_path, time_limit=None, verbose=False):
        super().__init__(wait_range, chromedriver_path, time_limit, verbose)
        self.root = 'https://www.beenverified.com/app/dashboard'

        site_specific_error_strings = dict()

        # Add to the base class error dict
        for key, value in site_specific_error_strings.items():
            self._error_strings[key] = value

    def auto_login(self, config_path, cookie_file):
        """

        :param config_path:
        :param cookie_file:
        :return:
        """
        config = get_config(config_path=config_path)
        login_url = self.root + '/login'
        try:
            if os.path.isfile(cookie_file):
                # Does this do anything useful? WHO KNOWS!!!!!!!!
                self.load_session_cookies(cookie_file)
            self._load_page(login_url)
        except ScraperException as e:
            raise ScraperException('Unable to load login page: {}. {}'.format(login_url, e))

        email_input = self._driver.find_element_by_css_selector("input[type='email']")
        pass_input = self._driver.find_element_by_css_selector("input[type='password']")

        email_input.send_keys(config['email'])
        pass_input.send_keys(config['pass'])
        pass_input.send_keys(Keys.RETURN)

        # Verify login success
        success = False
        while not success:
            try:
                self._driver.find_element_by_id('recent_reports_table')
                success = True
            except NoSuchElementException:
                time.sleep(2)

        print('Login successful')
