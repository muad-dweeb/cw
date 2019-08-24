import os
import sys
from argparse import ArgumentParser
from selenium.common.exceptions import NoSuchWindowException

from ICScraper import ICScraper
from SheetConfig import SheetConfig
from exceptions import ScraperException, SheetConfigException


def validate_config_dict(config_dict):
    """
    location, id_column, and id_char_count are pre-validated by the SheetConfig class
    The validated keys here are specific to this CLI's usage
    :param config_dict: a dict
    :return: Boolean
    """
    required_keys = {'first_name_column', 'last_name_column'}
    for key in required_keys:
        if key not in config_dict.keys():
            raise SheetConfigException('Required key \'{}\' missing from config dict'.format(key))
        if type(config_dict[key]) != str:
            raise SheetConfigException('Config key \'{}\' must be type str, not {}. '
                                       'Value: {}'.format(key, type(config_dict[key]), config_dict[key]))


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--config', required=True, help='Configuration name')
    parser.add_argument('--limit-rows', type=int, help='Number of Sheet rows to limit scraping to')
    args = parser.parse_args()

    config = None
    scraper = None

    # Load Configuration
    try:
        config = SheetConfig(args.config)
        validate_config_dict(config.dict)
        sheet_path = os.path.expanduser(config.location)
    except SheetConfigException as e:
        print('Failed to load sheet config \'{}\'. Error: {}'.format(args.config, e))
        sys.exit(1)

    # Scrape
    try:
        scraper = ICScraper()
        scraper.manual_login()

        # TESTING
        contact_info = scraper.get_all_info('andrew', 'galloway', 'seattle', 'wa')
        print(contact_info)

    except ScraperException as e:
        print('Scrape failed. Error: {}'.format(e))

    except NoSuchWindowException:
        print('Window was closed prematurely')

    if scraper:
        scraper.close()
