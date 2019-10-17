import sys
import traceback
from argparse import ArgumentParser
from copy import deepcopy
from csv import DictReader, DictWriter
from datetime import datetime, timedelta
from os import path
from re import compile

from selenium.common.exceptions import NoSuchWindowException

from ICScraper import ICScraper
from SheetConfig import SheetConfig
from SheetManager import SheetManager
from exceptions import ScraperException, SheetConfigException


SEP = '-' * 60


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

    return_dict['count'] = len(return_dict['first_names'])

    return return_dict


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--config', required=True, help='Configuration name')
    parser.add_argument('--limit-rows', required=False, type=int, help='Number of Sheet rows to limit scraping to')
    parser.add_argument('--limit-minutes', required=False, type=int, help='Number of minutes to limit scraping to')
    parser.add_argument('--verbose', default=False, help='Increase print verbosity', action='store_true')
    args = parser.parse_args()

    config = None
    scraper = None
    time_limit = None

    verbose = args.verbose
    limit_rows = args.limit_rows
    limit_minutes = args.limit_minutes

    # Load required files
    try:
        # Config
        config = SheetConfig(args.config)
        validate_config_dict(config.dict)

        # Input Sheet
        in_file = path.expanduser(config.location)
        print('Reading from:   {}'.format(in_file))
        sheet_reader = DictReader(open(path.expanduser(in_file)))
        column_dict = get_columns(sheet_reader, config.dict)

        # Output Sheet
        out_file = SheetManager.create_new_filename(in_path=in_file, overwrite_existing=True)

    except SheetConfigException as e:
        print('Failed to load sheet config \'{}\'. Error: {}'.format(args.config, e))
        sys.exit(1)

    # User prompt if out_file already exists; warn of overwrite!
    if path.isfile(out_file):
        print('WARNING: Output file already exists: {}'.format(out_file))
        overwrite = input('Do you wish to overwrite existing file? '
                          'All previous scrapes in this file will be lost!'
                          'yes/no')
        if overwrite.lower() != 'yes':
            print('Aborting scrape.')
            print('Either rename the file you wish to use as input to match the \'location\' value in the config, '
                  'or edit the config \'location\' value to match the input file you wish to use.')
            print('Config: {}'.format(args.config))
            sys.exit()

    # DO THE THING!
    try:
        scraper = ICScraper()
        scraper.manual_login()

        with open(out_file, 'w') as out:
            print('Writing to:     {}'.format(out_file))

            print(SEP)

            last_search = None
            current_search = {'first_name': None, 'last_name': None, 'city': None, 'state': None}

            # Output sheet will have at least the input sheet's columns
            output_columns = sheet_reader.fieldnames

            contact_columns = {'phone': list(), 'email': list()}

            index = 0
            while index < column_dict['count']:

                column_prefix = path.commonprefix([column_dict['first_names'][index], column_dict['last_names'][index]])
                phone_column = '{} Phone'.format(column_prefix)
                email_column = '{} Email'.format(column_prefix)

                contact_columns['phone'].append(phone_column)
                contact_columns['email'].append(email_column)

                # Add contact columns to header as needed
                for contact_column in (phone_column, email_column):
                    if contact_column not in output_columns:
                        output_columns.append(contact_column)

                index += 1

            # 'scraped' column is a Boolean that simply confirms that a given row was previously auto-scraped
            if 'scraped' not in output_columns:
                output_columns.append('scraped')

            # Initialize output sheet with header
            sheet_writer = DictWriter(out, fieldnames=output_columns)
            sheet_writer.writeheader()

            # Iterate through rows in the spreadsheet
            start_time = datetime.now()
            # TODO: The following print would be rendered obsolete with a decently-formatted logger
            print('Beginning scrape at {}'.format(start_time))
            if limit_minutes is not None:
                time_limit = start_time + timedelta(minutes=limit_minutes)
                print('Estimated end at {}'.format(time_limit))
            print(SEP)

            row_count = 0
            for row in sheet_reader:

                # Skip already-scraped rows
                if 'scraped' in row.keys() and row['scraped'] is True:
                    continue

                output_row = deepcopy(row)
                grouped_contact_dict = dict()

                # Iterate through groups of columns
                index = 0
                while index < column_dict['count']:
                    first_name = row[column_dict['first_names'][index]].strip().upper()
                    last_name = row[column_dict['last_names'][index]].strip().upper()
                    city = row[column_dict['cities'][index]].strip().upper()
                    state = row[column_dict['states'][index]].strip().upper()

                    grouped_contact_dict[index] = {'phone_numbers': list(), 'email_addresses': list()}

                    # Skip empty column groups
                    if first_name not in (None, '') and last_name not in (None, ''):

                        # Only increment this if the row has the required data
                        row_count += 1

                        current_search['first_name'] = first_name
                        current_search['last_name'] = last_name
                        current_search['city'] = city
                        current_search['state'] = state

                        if current_search != last_search:
                            if verbose:
                                print('Search: {} ({}) , ({}) ({})'.format(first_name, last_name, city, state))

                            # Use the current search params to scrape contact info
                            contact_info = scraper.get_all_info(first=first_name, last=last_name, city=city, state=state)

                            last_search = deepcopy(current_search)

                        else:
                            if verbose:
                                print('\t  Skipping duplicate search...')

                            # Reuse the last scraped contact info
                            contact_info = scraper.last_contact_info

                        grouped_contact_dict[index] = contact_info

                    index += 1

                for contact_index, contact_info in grouped_contact_dict.items():
                    phone_numbers = list(contact_info['phone_numbers'])
                    email_addresses = list(contact_info['email_addresses'])

                    # Write contact info to output row
                    if len(phone_numbers) > 0:
                        output_row[contact_columns['phone'][contact_index]] = ','.join(phone_numbers)
                    if len(email_addresses) > 0:
                        output_row[contact_columns['email'][contact_index]] = ','.join(email_addresses)

                    # TODO: split the phone numbers and email addresses across multiple rows (VERY DIFFICULT)

                # Mark row as scraped to prevent future re-scrape
                output_row['scraped'] = True

                # Write out the completed row
                sheet_writer.writerow(output_row)

                print(SEP)

                if limit_rows is not None and row_count >= limit_rows:
                    print('Row limit ({}) reached!'.format(limit_rows))
                    break

                if time_limit is not None and datetime.now() >= time_limit:
                    print('Minute limit ({}) reached!'.format(limit_minutes))
                    break

    except ScraperException as e:
        print('Scrape failed. Error: {}'.format(e))

    except NoSuchWindowException:
        print('Window was closed prematurely')

    except Exception as e:
        print('Unhandled exception: {}'.format(e))
        traceback.print_exc()

    if scraper:
        scraper.close()
