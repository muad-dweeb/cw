import sys
import traceback
from argparse import ArgumentParser
from copy import deepcopy
from csv import DictReader, DictWriter
from datetime import datetime, timedelta
from os import path, getpid
from re import compile

from selenium.common.exceptions import NoSuchWindowException

# from scrape.BVScraper import BVScraper
from scrape.Caffeine import Caffeine
from scrape.FpsScraper import FpsScraper
from scrape.ICScraper import ICScraper
from SheetConfig import SheetConfig
from exceptions import ScraperException, SheetConfigException
from scrape.util import random_sleep
from util import create_new_filename

SEP = '-' * 60
SITES = {'ic', 'fps'}


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


def row_should_be_skipped(row_scraped_value):
    """
    :param row_scraped_value: Value read from 'scraped' column
    :return: Boolean
    """
    if row_scraped_value is None:
        return False
    elif row_scraped_value.lower() in ('failed', 'skip'):
        return True
    elif row_scraped_value.lower() in SITES:
        return True
    # Legacy compatibility
    elif bool(row_scraped_value) is True:
        return True
    else:
        return False


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--config', required=True, help='Configuration name')
    parser.add_argument('--limit-rows', required=False, type=int, help='Number of Sheet rows to limit scraping to')
    parser.add_argument('--limit-minutes', required=False, type=int, help='Number of minutes to limit scraping to')
    parser.add_argument('--verbose', default=False, help='Increase print verbosity', action='store_true')
    parser.add_argument('--auto-close', default=False, help='Close the browser when finished', action='store_true')
    parser.add_argument('--site', required=True, choices=SITES,
                        help='The site to scrape: instantcheckmate.com (ic) or fastpeoplesearch.com (fps)')
    args = parser.parse_args()

    limit_rows = args.limit_rows
    limit_minutes = args.limit_minutes
    verbose = args.verbose
    auto_close = args.auto_close
    site = args.site

    config = None
    scraper = None
    time_limit = None
    row_count = 0
    scraped_count = 0
    failed_count = 0

    # Seconds between searches, randomized to hopefully throw off bot-detection
    if site == 'fps':
        wait_range_between_rows = (15, 120)
        wait_range_between_report_loads = (5, 15)
    else:
        wait_range_between_rows = (30, 500)  # 0.5 - 7.5 minutes
        wait_range_between_report_loads = (20, 60)

    # Not sure if there's actually any benefit to this
    cookie_file = path.join(path.dirname(path.dirname(path.abspath(__file__))),
                            'data', '.{}_cookie_jar.pkl'.format(site))

    # Don't let the computer go to sleep, else it will kill the scraper
    pid = getpid()
    Caffeine().start(pid)

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
        out_file = create_new_filename(in_path=in_file, overwrite_existing=True)

    except SheetConfigException as e:
        print('Failed to load sheet config \'{}\'. Error: {}'.format(args.config, e))
        sys.exit(1)

    start_time = datetime.now()
    # TODO: The following print would be rendered obsolete with a decently-formatted logger
    print('Beginning scrape at {}'.format(start_time))

    # DO THE THING!
    try:

        if limit_minutes is not None:
            time_limit = start_time + timedelta(minutes=limit_minutes)
            print('Run limited to {} minutes'.format(limit_minutes))
            print('Estimated end at {}'.format(time_limit))

        if limit_rows is not None:
            print('Run limited to {} rows'.format(limit_rows))

        # User prompt if out_file already exists; warn of overwrite!
        if path.isfile(out_file):
            print(SEP)
            print('WARNING: Output file already exists: {}'.format(out_file))
            overwrite = input('Do you wish to overwrite existing file? '
                              'All previous scrapes in this file will be lost! '
                              '(yes/no)\n')
            if overwrite.lower() != 'yes':
                print('Aborting scrape.')
                print('Either rename the file you wish to use as input to match the \'location\' value in the config, '
                      'or edit the config \'location\' value to match the input file you wish to use.')
                print('Config: {}'.format(args.config))
                sys.exit()

        if site == 'ic':
            scraper = ICScraper(wait_range=wait_range_between_report_loads, time_limit=time_limit,
                                use_proxy=False, verbose=verbose)
            scraper.manual_login(cookie_file)

        # elif site == 'bv':
        #     scraper = BVScraper(wait_range=wait_range_between_report_loads, time_limit=time_limit, verbose=verbose)
        #     scraper.auto_login(cookie_file)

        elif site == 'fps':
            scraper = FpsScraper(wait_range=wait_range_between_report_loads, time_limit=time_limit, verbose=verbose)
            scraper.auto_login(cookie_file)

        else:
            print('Site \'{}\' not supported. Exiting.'.format(site))
            sys.exit()

        with open(out_file, 'w') as out:
            print('Writing to:     {}'.format(out_file))

            print(SEP)

            last_search = None
            current_search = {'first_name': None, 'last_name': None, 'city': None, 'state': None}

            # Output sheet will have at least the input sheet's columns
            output_columns = sheet_reader.fieldnames

            contact_columns = {'phone': list(), 'email': list()}

            column_index = 0
            while column_index < column_dict['count']:

                column_prefix = path.commonprefix([column_dict['first_names'][column_index],
                                                   column_dict['last_names'][column_index]])
                phone_column = '{} Phone'.format(column_prefix)
                email_column = '{} Email'.format(column_prefix)

                contact_columns['phone'].append(phone_column)
                contact_columns['email'].append(email_column)

                # Add contact columns to header as needed
                for contact_column in (phone_column, email_column):
                    if contact_column not in output_columns:
                        output_columns.append(contact_column)

                column_index += 1

            # 'scraped' column is a flag that simply confirms that a given row was previously auto-scraped
            if 'scraped' not in output_columns:
                output_columns.append('scraped')

            # Initialize output sheet with header
            sheet_writer = DictWriter(out, fieldnames=output_columns)
            sheet_writer.writeheader()

            last_row = None
            last_search_was_duplicate = False
            last_row_was_duplicate = False
            found_results = False

            # Iterate through rows in the spreadsheet
            for row in sheet_reader:

                row_count += 1

                # Hacky crap
                # TODO: something about this flag is causing the first row to always say "Skipping duplicate row"
                if row_count == 1:
                    duplicate_row = False
                else:
                    duplicate_row = True

                # Skip already-scraped rows
                if 'scraped' in row.keys() and row_should_be_skipped(row_scraped_value=row['scraped']):
                    if verbose:
                        print('Skipping row with \'scraped\' value: \'{}\''.format(row['scraped']))
                    sheet_writer.writerow(row)
                    continue

                print(SEP)

                # Randomized wait in between searches
                if scraped_count > 0 and not last_search_was_duplicate and not last_row_was_duplicate:
                    if found_results:
                        random_sleep(wait_range_between_rows, verbose=verbose)
                    else:
                        # A shorter wait time if 0 matching results were found for a row
                        random_sleep(wait_range_between_report_loads, verbose=verbose)

                found_results = False
                output_row = deepcopy(row)
                grouped_contact_dict = dict()

                # Iterate through groups of columns
                index = 0
                while index < column_dict['count']:
                    first_name = row[column_dict['first_names'][index]].strip().upper()
                    last_name = row[column_dict['last_names'][index]].strip().upper()
                    city = row[column_dict['cities'][index]].strip().upper()
                    state = row[column_dict['states'][index]].strip().upper()

                    # Skip duplicate rows
                    if last_row is not None:
                        if first_name == last_row[column_dict['first_names'][index]].strip().upper() and \
                            last_name == last_row[column_dict['last_names'][index]].strip().upper() and \
                            city == last_row[column_dict['cities'][index]].strip().upper() and \
                            state == last_row[column_dict['states'][index]].strip().upper():
                            output_row[contact_columns['phone'][contact_index]] = \
                                last_row[contact_columns['phone'][contact_index]]
                            output_row[contact_columns['email'][contact_index]] = \
                                last_row[contact_columns['email'][contact_index]]
                            index += 1
                            found_results = True
                            continue
                        else:
                            duplicate_row = False

                    grouped_contact_dict[index] = {'phone_numbers': list(), 'email_addresses': list()}

                    # Skip empty column groups
                    if first_name not in (None, '') and last_name not in (None, ''):

                        current_search['first_name'] = first_name
                        current_search['last_name'] = last_name
                        current_search['city'] = city
                        current_search['state'] = state

                        if current_search != last_search:
                            if verbose:
                                print('Search: {} {}, {} {}'.format(first_name, last_name, city, state))

                            # Short wait in between all report loads
                            if scraped_count > 1:
                                random_sleep(wait_range_between_report_loads, verbose=True)

                            # Use the current search params to scrape contact info
                            contact_info = scraper.get_all_info(first=first_name, last=last_name, city=city, state=state)

                            last_search = deepcopy(current_search)
                            last_search_was_duplicate = False

                        else:
                            if verbose:
                                print('\t  Skipping duplicate search...')
                                last_search_was_duplicate = True

                            # Reuse the last scraped contact info
                            contact_info = scraper.last_contact_info

                        grouped_contact_dict[index] = contact_info

                    index += 1

                if duplicate_row:
                    last_row_was_duplicate = True
                    if verbose:
                        print('\t  Skipping duplicate row...')
                else:
                    last_row_was_duplicate = False

                for contact_index, contact_info in grouped_contact_dict.items():
                    phone_numbers = list(contact_info['phone_numbers'])
                    email_addresses = list(contact_info['email_addresses'])

                    # Write contact info to output row
                    if len(phone_numbers) > 0:
                        found_results = True
                        output_row[contact_columns['phone'][contact_index]] = ', '.join(phone_numbers)
                    if len(email_addresses) > 0:
                        found_results = True
                        output_row[contact_columns['email'][contact_index]] = ', '.join(email_addresses)

                    # TODO: split the phone numbers and email addresses across multiple rows (VERY DIFFICULT)

                if found_results:
                    # Mark row as scraped to prevent future re-scrape
                    output_row['scraped'] = site
                    scraped_count += 1
                else:
                    output_row['scraped'] = 'failed'
                    failed_count += 1

                # Write out the completed row
                sheet_writer.writerow(output_row)

                if limit_rows is not None and scraped_count >= limit_rows:
                    print('Row limit ({}) reached!'.format(limit_rows))
                    break

                if time_limit is not None and datetime.now() >= time_limit:
                    print('Minute limit ({}) reached!'.format(limit_minutes))
                    break

                last_row = output_row

    except ScraperException as e:
        print('Scrape failed. Error: {}'.format(e))

    except NoSuchWindowException:
        print('Window was closed prematurely.')

    except KeyboardInterrupt:
        print('Run interrupted by User.')

    except Exception as e:
        print('Unhandled exception: {}'.format(e))
        traceback.print_exc()

    if scraper and auto_close:
        scraper.close()

    end_time = datetime.now()
    duration = end_time - start_time
    print(SEP)
    print('Scrape completed at {}'.format(end_time))
    print('Total run time: {}'.format(duration))
    print('Total rows processed: {}'.format(row_count))
    print('Total rows successfully scraped: {}'.format(scraped_count))
    print('Total rows failed to scrape: {}'.format(failed_count))
    print('Total reports loaded: {}'.format(scraper.reports_loaded))
