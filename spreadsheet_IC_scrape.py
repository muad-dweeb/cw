import sys
from argparse import ArgumentParser
from csv import DictReader
from os import path
from re import compile

from selenium.common.exceptions import NoSuchWindowException

from ICScraper import ICScraper
from SheetConfig import SheetConfig
from exceptions import ScraperException, SheetConfigException


def validate_config_dict(config_dict):
    """
    location, id_column, and id_char_count are pre-validated by the SheetConfig class
    The validated keys here are specific to this CLI's usage
    :param config_dict: a dict
    """
    required_keys = {'first_name_column', 'last_name_column', 'city_column', 'state_column'}
    for key in required_keys:
        if key not in config_dict.keys():
            raise SheetConfigException('Required key \'{}\' missing from config dict'.format(key))
        if type(config_dict[key]) != str:
            raise SheetConfigException('Config key \'{}\' must be type str, not {}. '
                                       'Value: {}'.format(key, type(config_dict[key]), config_dict[key]))


def get_columns(dict_reader, config_dict):
    """
    Parse out and validate all columns to be used for search parameters
    :param dict_reader: a csv.DictReader object
    :param config_dict: dict containing regex patterns
    :return: validated dict
    """
    columns = dict_reader.fieldnames

    regex_mapping = {
        'first_names': compile(config_dict['first_name_column']),
        'last_names': compile(config_dict['last_name_column']),
        'cities': compile(config_dict['city_column']),
        'states': compile(config_dict['state_column'])
    }

    # Disparate columns will need to be associated with each other by index
    # So, it's important that these lists are ordered correctly
    return_dict = {
        'first_names': list(),
        'last_names': list(),
        'cities': list(),
        'states': list()
    }

    # Build return dict
    for column in columns:
        for key, regex in regex_mapping.items():
            if regex.match(column):
                return_dict[key].append(column)

    # Basic empty list validation
    for key, value in return_dict.items():
        if len(value) == 0:
            raise SheetConfigException('No columns were extracted for {}'.format(key))

    # Make sure each first name has a corresponding last name and vice-versa
    if len(return_dict['first_names']) != len(return_dict['last_names']):
        print('first_names column count: {}'.format(len(return_dict['first_names'])))
        print('last_names column count: {}'.format(len(return_dict['last_names'])))
        raise SheetConfigException('Number of first-name columns must match number of last-name columns!')

    # If only one city/state column exists, it will be used for all names,
    #  otherwise, there must be a corresponding city/state for every name.
    for location_key in ['cities', 'states']:
        if len(return_dict[location_key]) > 1:
            if len(return_dict[location_key]) != len(return_dict['first_names']):
                raise SheetConfigException('Number of {} columns is greater than 1 '
                                           'but does not match the number of names'.format(location_key))
        else:
            while len(return_dict[location_key]) < len(return_dict['first_names']):
                return_dict[location_key].append(return_dict[location_key][0])

    return return_dict


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--config', required=True, help='Configuration name')
    parser.add_argument('--limit-rows', type=int, help='Number of Sheet rows to limit scraping to')
    args = parser.parse_args()

    config = None
    scraper = None

    # Load Configuration and Sheet
    try:
        config = SheetConfig(args.config)
        validate_config_dict(config.dict)
        sheet_reader = DictReader(open(path.expanduser(config.location)))
        column_dict = get_columns(sheet_reader, config.dict)

    except SheetConfigException as e:
        print('Failed to load sheet config \'{}\'. Error: {}'.format(args.config, e))
        sys.exit(1)

    # TESTING
    print(column_dict)

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
