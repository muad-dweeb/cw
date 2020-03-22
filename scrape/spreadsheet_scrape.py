import sys
from argparse import ArgumentParser
from copy import deepcopy
from csv import DictReader, DictWriter
from datetime import datetime, timedelta
from os import path, getpid
from re import compile
from socket import gethostname
from time import sleep

from botocore.exceptions import ClientError
from selenium.common.exceptions import NoSuchWindowException

from SheetConfig import SheetConfig
from lib.exceptions import ScraperException, SheetConfigException
from lib.util import create_new_filename, upload_file, get_current_ec2_instance_id, shutdown_ec2_instance, \
    get_current_ec2_instance_region, create_logger, create_s3_object_key
# from scrape.BVScraper import BVScraper
from scrape.Caffeine import Caffeine
from scrape.FpsScraper import FpsScraper
from scrape.ICScraper import ICScraper
from scrape.RunConfig import RunConfig


SUPPORTED_SITES = {'fps', 'ic'}

# Print separator
SEP = '-' * 60


def validate_sheet_config_dict(config_dict):
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
        logger.error('first_names column count: {}'.format(len(return_dict['first_names'])))
        logger.error('last_names column count: {}'.format(len(return_dict['last_names'])))
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
    elif row_scraped_value.lower() in SUPPORTED_SITES:
        return True
    # Legacy compatibility
    elif bool(row_scraped_value) is True:
        return True
    else:
        return False


def main(config_path, site, environment, limit_rows=None, limit_minutes=None, auto_close=None):
    scraper = None
    time_limit = None

    metrics = {'row_count': 0,
               'scraped_count': 0,
               'failed_count': 0}

    hostname = gethostname()

    # Path to the chromedriver executable; as downloaded by the install_chrome script
    chromedriver_path = path.join(path.dirname(path.dirname(path.abspath(__file__))), 'lib', 'chromedriver')

    # Not sure if there's actually any benefit to this
    cookie_file = path.join(path.dirname(path.dirname(path.abspath(__file__))),
                            'data', '.{}_cookie_jar.pkl'.format(site))

    # Don't let the computer go to sleep, else it will kill the scraper
    pid = getpid()
    try:
        Caffeine().start(pid)
    except NotImplementedError as e:
        logger.warning(e)

    # Load required files
    try:
        # Sheet Config
        sheet_config = SheetConfig(config_path)
        validate_sheet_config_dict(sheet_config.dict)

        # Run Config
        run_config = RunConfig(site_key=site)

        # Input Sheet
        in_file = path.expanduser(sheet_config.location)
        logger.info('Reading from:   {}'.format(in_file))
        sheet_reader = DictReader(open(path.expanduser(in_file)))
        column_dict = get_columns(sheet_reader, sheet_config.dict)

        # Output Sheet
        out_file = create_new_filename(in_path=in_file, overwrite_existing=True)

    except SheetConfigException as e:
        logger.exception('Failed to load sheet config \'{}\'. Error: {}'.format(config_path, e))
        sys.exit(1)

    except KeyError as e:
        logger.exception('Failed to load run config \'{}\'. Error: {}'.format(RunConfig.CONFIG_PATH, e))
        sys.exit(1)

    start_time = datetime.now()
    logger.info('Beginning scrape')

    # DO THE THING!
    try:

        if limit_minutes is not None:
            time_limit = start_time + timedelta(minutes=limit_minutes)
            logger.info('Run limited to {} minutes'.format(limit_minutes))
            logger.info('Estimated end at {}'.format(time_limit))

        if limit_rows is not None:
            logger.info('Run limited to {} rows'.format(limit_rows))

        # User prompt if out_file already exists; warn of overwrite!
        if path.isfile(out_file):
            logger.warning('Output file already exists: {}'.format(out_file))
            overwrite = input('Do you wish to overwrite existing file? '
                              'All previous scrapes in this file will be lost! '
                              '(yes/no)\n')
            if overwrite.lower() != 'yes':
                logger.warning('Aborting scrape.')
                logger.info('Either rename the file you wish to use as input to match the \'location\' value in the '
                            'config, or edit the config \'location\' value to match the input file you wish to use.')
                logger.info('Config: {}'.format(config_path))
                sys.exit()

        if site == 'ic':
            scraper = ICScraper(logger=logger, wait_range=run_config.wait_range_between_report_loads,
                                chromedriver_path=chromedriver_path, time_limit=time_limit, use_proxy=False)
            scraper.manual_login(cookie_file)

        # elif site == 'bv':
        #     scraper = BVScraper(logger=logger, wait_range=wait_range_between_report_loads, time_limit=time_limit)
        #     scraper.auto_login(cookie_file)

        elif site == 'fps':
            scraper = FpsScraper(logger=logger, wait_range=run_config.wait_range_between_report_loads,
                                 chromedriver_path=chromedriver_path, time_limit=time_limit)
            scraper.auto_login(cookie_file)

        else:
            logger.error('Site \'{}\' not supported. Exiting.'.format(site))
            sys.exit()

        with open(out_file, 'w') as out:
            logger.info('Writing to:     {}'.format(out_file))

            last_search = None
            current_search = {'first_name': None, 'last_name': None, 'city': None, 'state': None}
            contact_columns = {'phone': list(), 'email': list()}

            # Output sheet will have at least the input sheet's columns
            output_columns = sheet_reader.fieldnames

            # Build initial output column list
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

                metrics['row_count'] += 1

                # Hacky crap
                # TODO: something about this flag is causing the first row to always say "Skipping duplicate row"
                if metrics['row_count'] == 1:
                    duplicate_row = False
                else:
                    duplicate_row = True

                # Skip already-scraped rows
                if 'scraped' in row.keys() and row_should_be_skipped(row_scraped_value=row['scraped']):
                    logger.debug('Skipping row {} with \'scraped\' value: \'{}\''.format(metrics['row_count'],
                                                                                         row['scraped']))
                    sheet_writer.writerow(row)
                    continue

                if 'hostname' in row.keys() and row['hostname'] != hostname:
                    logger.debug('Skipping row {} with hostname \'{}\''.format(metrics['row_count'],
                                                                               row['hostname']))
                    sheet_writer.writerow(row)
                    continue

                # Randomized wait in between searches
                if metrics['scraped_count'] > 0 and not last_search_was_duplicate and not last_row_was_duplicate:
                    if found_results:
                        scraper.random_sleep(run_config.wait_range_between_rows)
                    else:
                        # A shorter wait time if 0 matching results were found for a row
                        scraper.random_sleep(run_config.wait_range_between_report_loads)

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
                            logger.debug('Search: {} {}, {} {}'.format(first_name, last_name, city, state))

                            # Short wait in between all report loads
                            if metrics['scraped_count'] > 1:
                                scraper.random_sleep(run_config.wait_range_between_report_loads)

                            # Use the current search params to scrape contact info
                            contact_info = scraper.get_all_info(first=first_name, last=last_name, city=city,
                                                                state=state)

                            last_search = deepcopy(current_search)
                            last_search_was_duplicate = False

                        else:
                            logger.debug('\t  Skipping duplicate search...')
                            last_search_was_duplicate = True

                            # Reuse the last scraped contact info
                            contact_info = scraper.last_contact_info

                        grouped_contact_dict[index] = contact_info

                    index += 1

                if duplicate_row:
                    last_row_was_duplicate = True
                    logger.debug('\t  Skipping duplicate row...')
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
                    metrics['scraped_count'] += 1
                else:
                    output_row['scraped'] = 'failed'
                    metrics['failed_count'] += 1

                # Write out the completed row
                sheet_writer.writerow(output_row)

                if limit_rows is not None and metrics['scraped_count'] >= limit_rows:
                    logger.info('Row limit ({}) reached!'.format(limit_rows))
                    break

                if time_limit is not None and datetime.now() >= time_limit:
                    logger.info('Minute limit ({}) reached!'.format(limit_minutes))
                    break

                last_row = output_row

    except ScraperException as e:
        logger.exception('Scrape failed. Error: {}'.format(e))

    except NoSuchWindowException:
        logger.error('Window was closed prematurely.')

    except KeyboardInterrupt:
        logger.error('Run interrupted by User.')

    except Exception as e:
        logger.exception('Unhandled exception: {}'.format(e))

    # Close the browser
    if scraper and auto_close:
        scraper.close()

    # Upload out_file to s3 bucket
    if environment == 'ec2':
        object_name = create_s3_object_key(local_file_path=out_file, hostname=hostname)
        try:
            logger.info('Uploading {} to {}/{}'.format(out_file, run_config.upload_bucket, object_name))
            upload_file(file_name=out_file, bucket=run_config.upload_bucket, object_name=object_name)
        except ClientError as e:
            logger.exception('S3 upload failed: {}'.format(e))

    # Metrics!
    metrics['end_time'] = datetime.now()
    metrics['duration'] = metrics['end_time'] - start_time
    metrics['reports_loaded'] = scraper.reports_loaded
    print(SEP)
    print('Scrape completed at {}'.format(metrics['end_time']))
    print('Total run time: {}'.format(metrics['duration']))
    print('Total rows processed: {}'.format(metrics['row_count']))
    print('Total rows successfully scraped: {}'.format(metrics['scraped_count']))
    print('Total rows failed to scrape: {}'.format(metrics['failed_count']))
    print('Total reports loaded: {}'.format(metrics['reports_loaded']))

    # Power down instance to save utilization costs
    if environment == 'ec2':
        instance_id = get_current_ec2_instance_id()
        instance_region = get_current_ec2_instance_region()
        logger.info('Shutting down Instance {} in 10 seconds...'.format(instance_id))
        sleep(10)
        shutdown_ec2_instance(instance_id=instance_id, region=instance_region)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--config', required=True, help='Configuration name')
    parser.add_argument('--limit-rows', required=False, type=int, help='Number of Sheet rows to limit scraping to')
    parser.add_argument('--limit-minutes', required=False, type=int, help='Number of minutes to limit scraping to')
    parser.add_argument('--debug', default=False, help='Increase logger verbosity', action='store_true')
    parser.add_argument('--auto-close', default=False, help='Close the browser when finished', action='store_true')
    parser.add_argument('--site', required=True, choices=SUPPORTED_SITES,
                        help='The site to scrape: instantcheckmate.com (ic) or fastpeoplesearch.com (fps)')
    parser.add_argument('--environment', '-e', required=True, choices={'ec2', 'local'})

    args = parser.parse_args()

    logger = create_logger(caller=__file__, debug=args.debug)

    main(config_path=args.config,
         site=args.site,
         environment=args.environment,
         limit_rows=args.limit_rows,
         limit_minutes=args.limit_minutes,
         auto_close=args.auto_close)
