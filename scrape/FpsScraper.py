import os
import time

from selenium.common.exceptions import NoSuchElementException

from exceptions import ScraperException
from scrape.Scraper import Scraper


class FpsScraper(Scraper):

    def __init__(self, wait_range, time_limit=None, verbose=False):
        super().__init__(wait_range, time_limit, verbose)
        self.root = 'https://www.fastpeoplesearch.com/'
        # TODO: Only going to find these error strings as they occur; see ICScraper for format
        self._error_strings = {}

    def auto_login(self, cookie_file):
        """
        Not really a "login" method, since there's no account wall on fastpeoplesearch.com
        :param cookie_file:
        :return:
        """
        try:
            self._load_page(self.root)
            if os.path.isfile(cookie_file):
                # Does this do anything useful? WHO KNOWS!!!!!!!!
                self.load_session_cookies(cookie_file)
                self._driver.refresh()
            self.save_session_cookies(cookie_file)
            print('Site load successful')
        except ScraperException as e:
            raise ScraperException('Unable to load main page: {}. {}'.format(self.root, e))

    def find(self, first, last, city, state, verbose=False):
        """
        Performs the search and filters out false positives
        :return: list of
        """
        matches = list()

        search_url = self.root + '/name/{}-{}_{}-{}'.format(first, last, city, state)
        try:
            self._load_page(search_url)
        except ScraperException as e:
            raise ScraperException('Failed to load search page: {}. Error: {}'.format(search_url, e))

        results_list = self._driver.find_elements_by_class_name('card-block')
        for relevant_result in self._relevant_search_matches(results_list, first, last, city, state, verbose=verbose):
            matches.append(relevant_result)

        # Nothing found, slightly loosen the matching criteria and try again
        if len(matches) == 0:
            for relevant_result in self._relevant_search_matches(results_list, first, last, city, state, fuzzy=True,
                                                                 verbose=False):
                matches.append(relevant_result)

        # Free memory
        del results_list

        return matches

    def _relevant_search_matches(self, results_list, first, last, city, state, fuzzy=False, verbose=False):
        for result in results_list:
            found_age = None
            found_full = None

            result_text = result.text.split('\n')

            # The first line is always the simplified name (in some cases it may be the only one)
            found_simple_name = result_text.pop(0)

            # The second line is sometimes an alias, throw this away too
            if result_text[0].lower().startswith('goes by'):
                result_text.pop(0)

            # The next line SHOULD be the location (in rare occasions it does not exist)
            if ', ' not in result_text[0]:
                continue
            location_components = result_text.pop(0).strip().split(', ')
            found_city = location_components[0]
            found_state = location_components[1]

            for line in result_text:
                # Stop looking for them if we already found them
                if found_age is not None and found_full is not None:
                    break
                if line.startswith('Age:'):
                    found_age = line.lstrip('Age: ').strip()
                elif line.startswith('Full Name:'):
                    found_full = line.lstrip('Full Name: ').strip()

            # Don't call dead people, they aren't likely to answer
            if found_age is not None and 'deceased' in found_age.lower():
                continue

            # Allow using the simple header name in lieu of no Full Name existing, if fuzzy is allowed
            if found_full is None:
                if fuzzy:
                    found_full = found_simple_name
                else:
                    continue

            elif not self._validate_result_name(first, last, found_full):
                continue

            # Validation against canonical location params
            if found_city.lower() != city.lower() or found_state.lower() != state.lower():
                continue

            if verbose and not fuzzy:
                print('Result: {}, Age: {}, City: {}, State: {}'.format(found_full, found_age, found_city, found_state))

            # Only keep 100% input matches
            yield result

    def _has_next_page(self):
        pagination_links = self._driver.find_element_by_class_name('pagination-links')
        if 'NEXT PAGE' in pagination_links.text.upper():
            return True
        else:
            return False

    @staticmethod
    def _validate_result_name(search_first, search_last, found_full):
        """
        Validation against canonical name params
        :return: Boolean
        """
        search_middle = None

        full_name_elements = found_full.split(' ')

        # Normalize all the things!
        full_name_elements = [x.lower() for x in full_name_elements]
        search_first = search_first.lower()
        search_last = search_last.lower()

        # Some cells have a combined first/middle name
        if len(search_first.split()) == 2:
            search_first, search_middle = search_first.split(' ')

            # Remove abbreviation period
            search_middle = search_middle.strip('.').lower()

        # Get rid of unnecessary titles
        for title in ['mr', 'mrs', 'ms', 'mister', 'misses', 'miss']:
            if title in full_name_elements:
                full_name_elements.remove(title)

        # Validate first and last
        for name in [search_first, search_last]:
            if name not in full_name_elements:
                return False
            else:
                full_name_elements.remove(name)

        if search_middle is not None:
            for element in full_name_elements:
                if not element.startswith(search_middle):
                    return False

        # All checks passed; cleared for launch
        return True

    def get_info(self, search_result):
        """
        Given a search result, open its report and return the relevant information
        :param search_result: WebElement
        :return: dict
        """

        report_timeout = 180
        main_report = None
        contact_dict = {'phone_numbers': dict(), 'email_addresses': list()}

        # Big green button
        open_report = search_result.find_element_by_link_text('VIEW FREE DETAILS')
        open_report.click()

        # Verify report generation success
        countdown_begin = time.time()
        success = False
        while not success:
            try:
                main_report = self._driver.find_element_by_id('site-content')
                success = True

            # Simply waiting for the report to load...
            except NoSuchElementException:
                time.sleep(2)

            # Generic time-out
            if time.time() - countdown_begin > report_timeout:
                raise ScraperException('Report failed to generate in {} seconds'.format(report_timeout))

        print('Report load successful')
        self.reports_loaded += 1

        # Primary phone section (max 8 before 'Show More...')
        try:
            phone_card = main_report.find_element_by_class_name('detail-box-phone')
            phone_numbers = self._parse_phone_numbers(phone_text_list=phone_card.text.split('\n'))
            for key, value in phone_numbers.items():
                contact_dict['phone_numbers'][key] = value
        except NoSuchElementException:
            pass

        # Paginated phone section - TODO: THIS IS BROKEN, phone_card.text is always ''; where the hell are the numbers?
        try:
            phone_card = main_report.find_element_by_id('collapsed-phones')
            phone_numbers = self._parse_phone_numbers(phone_text_list=phone_card.text.split('\n'))
            for key, value in phone_numbers.items():
                contact_dict['phone_numbers'][key] = value
        except NoSuchElementException:
            pass

        # Primary email section
        try:
            email_card = main_report.find_element_by_class_name('detail-box-email')
            for row in email_card.text.split('\n'):
                if '@' in row:
                    contact_dict['email_addresses'].append(row)
        except NoSuchElementException:
            pass

        return contact_dict

    @staticmethod
    def _parse_phone_numbers(phone_text_list):
        parsed_numbers = dict()
        for row in phone_text_list:
            if row == '' or 'show more' in row.lower():
                continue

            phone_number, phone_type = row.split(' - ')

            # Skip fax numbers
            if phone_type.lower() == 'fax':
                continue

            parsed_numbers[phone_number] = phone_type

        return parsed_numbers
