import csv
import traceback
from argparse import ArgumentParser
from copy import deepcopy
from datetime import datetime
from os import path

# import pandas

from sheet_config import SheetConfig, SheetConfigException


SEP = '-' * 40


class SheetManagerException(BaseException):
    pass


class SheetManager(object):

    def __init__(self, master_config, child_config, overwrite=False):

        # These are SheetConfig objects
        self._master_config = master_config
        self._child_config = child_config

        out_file = self._create_new_filename(path_prefix=self._master_config.location,
                                             overwrite_existing=overwrite)
        self.out_file = path.expanduser(out_file)

        # Required files
        master_csv_path = path.expanduser(self._master_config.location)
        child_csv_path = path.expanduser(self._child_config.location)

        # Sheet Existence validation
        for f in {master_csv_path, child_csv_path}:
            if path.isfile(f):
                print('Found file: {}'.format(f))
            else:
                raise SheetManagerException('{} is not a file.'.format(f))

        self.master_reader = csv.DictReader(open(master_csv_path))
        self.child_reader = csv.DictReader(open(child_csv_path))

    def merge(self):
        """ Merge child into master using match_column """

        remaining_child_rows = list()
        unwanted_child_ids = list()

        # Hold all children in memory
        total_children = 0
        for row in self.child_reader:
            total_children += 1

            # Only add child if its ID len matches the master config length!
            child_id = row[self._child_config.id_column]
            if len(self._normalize_uid(child_id)) == self._master_config.id_char_count:
                remaining_child_rows.append(row)
            else:
                unwanted_child_ids.append(child_id)

        print(SEP)
        print('Total child rows processed: {}'.format(total_children))
        print('Child rows with proper ID lengths: {}'.format(len(remaining_child_rows)))
        print('Child rows with incorrect ID lengths: {}'.format(len(unwanted_child_ids)))
        print(SEP)

        output_fieldnames = self.master_reader.fieldnames + self.child_reader.fieldnames
        with open(self.out_file, 'w') as out:
            print('Writing out to: {}'.format(self.out_file))
            output_writer = csv.DictWriter(out, output_fieldnames)

            # Initialize output CSV
            output_writer.writeheader()

            # Iterate through master rows
            for m_row in self.master_reader:
                out_dict = deepcopy(m_row)
                master_id = m_row[self._master_config.id_column]

                # Iterate through remaining children
                for c_row in remaining_child_rows:
                    child_id = c_row[self._child_config.id_column]

                    # Do the IDs match after normalization?
                    if self._normalize_uid(child_id) == self._normalize_uid(master_id):
                        print('    ID match: {}'.format(master_id))

                        # Add all children values to out_dict
                        for c_key, c_value in c_row.iteritems():
                            out_dict[c_key] = c_value

                        # Delete child from remaining children so it is never iterated over again
                        remaining_child_rows.remove(c_row)

                # Write completed out_dict to the output CSV file
                output_writer.writerow(out_dict)

            # Don't forget the orphan children!
            print('Appending {} unmatched child rows to the end of the file...'.format(len(remaining_child_rows)))
            for o_row in remaining_child_rows:
                output_writer.writerow(o_row)

        # Display unmatched child IDs for verification
        print(SEP)
        print('Child rows skipped due to ID length mismatch:')
        for c_id in unwanted_child_ids:
            print('    {}'.format(c_id))

    def prune(self):
        raise SheetManagerException('prune method not yet implemented')

    @staticmethod
    def _normalize_uid(uid):
        """ Delete hyphens and spaces from input string """
        return uid.replace('-', '').replace(' ', '')

    @staticmethod
    def _create_new_filename(path_prefix, overwrite_existing=False):
        """ Save to a new CSV file with an incrementing filename unless overwrite is requested """
        # YYYYMMDD
        now_string = datetime.now().strftime('%Y%m%d')
        # Remove any file extension from the path
        path_prefix = path.splitext(path_prefix)[0]
        full_path = '{}_{}.csv'.format(path_prefix, now_string)

        if not overwrite_existing:
            increment = 1
            while path.isfile(full_path):
                full_path = '{}_{}_{}.csv'.format(path_prefix, now_string, increment)
                increment += 1

        return full_path


# class SheetManagerPandas(object):
#
#     def __init__(self, master_config, child_config):
#         self._master_config = master_config
#         self._child_config = child_config
#
#         # Required files
#         self._master_csv_path = path.expanduser(self._master_config.location)
#         self._child_csv_path = path.expanduser(self._child_config.location)
#
#         # Sheet Existence validation
#         for f in {self._master_csv_path, self._child_csv_path}:
#             if path.isfile(f):
#                 print('Found file: {}'.format(f))
#             else:
#                 raise SheetManagerException('{} is not a file.'.format(f))
#
#         # Ingest the data
#         self.master = pandas.read_csv(self._master_csv_path, index_col=self._master_config.id_column)
#         self.child = pandas.read_csv(self._child_csv_path)
#
#         # Normalize the values in the id columns
#         self.__normalize_uid(self.master, self._master_config.id_column)
#         self.__normalize_uid(self.child, self._child_config.id_column)
#
#     def merge(self):
#         """ Merge child into master using match_column """
#
#         dup_col_suffix = '__y'
#
#         merged = self.master.merge(self.child,
#                                    how='outer',
#                                    left_index=True,
#                                    right_on=self._child_config.id_column,
#                                    suffixes=('', dup_col_suffix))
#
#         # Clean up duplicate columns
#         for index, row in merged.iterrows():
#             for col in merged.columns:
#                 if not col.endswith(dup_col_suffix):
#                     continue
#                 x = merged.loc[index, col.strip(dup_col_suffix)]
#                 y = merged.loc[index, col]
#                 # SKip NaN values
#                 if type(x) != str or type(y) != str:
#                     continue
#                 if x.lower() == y.lower():
#                     merged.loc[index, col] = pandas.np.nan
#
#         return merged
#
#     def prune(self):
#         raise SheetManagerException('prune method not yet implemented')
#
#     @staticmethod
#     def __normalize_uid(data_frame, column_name):
#         """ Normalize the discrepancies in UIDs from different source sheets for easier comparison """
#         for index, row in data_frame.iterrows():
#             if column_name in data_frame.columns:
#                 uid_in = data_frame.loc[index, column_name]
#                 uid_out = uid_in.replace('-', ' ')
#                 data_frame.loc[index, column_name] = uid_out
#             else:
#                 uid_in = data_frame.loc[index]
#                 uid_out = uid_in.replace('-', ' ')
#                 data_frame.loc[index] = uid_out
#
#     @staticmethod
#     def __validate_uniqueness(some_list):
#         """ Use this to validate UID columns """
#         if len(some_list) != len(set(some_list)):
#             return False
#         return True
#
#     @staticmethod
#     def create_new_filename(path_prefix, overwrite_existing=False):
#         """ Save to a new CSV file with an incrementing filename unless overwrite is requested """
#         # YYYYMMDD
#         now_string = datetime.now().strftime('%Y%m%d')
#         # Remove any file extension from the path
#         path_prefix = path.splitext(path_prefix)[0]
#         full_path = '{}_{}.csv'.format(path_prefix, now_string)
#
#         if not overwrite_existing:
#             increment = 1
#             while path.isfile(full_path):
#                 full_path = '{}_{}_{}.csv'.format(path_prefix, now_string, increment)
#                 increment += 1
#
#         return full_path


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--master-config', required=True, help='Path to the master sheet')
    parser.add_argument('--child-config',  required=True, help='Path to sheet to use for operating on the master sheet')
    parser.add_argument('--operation',     required=True, help='Operation to perform', choices={'merge', 'prune'})
    parser.add_argument('--overwrite',     default=False, action='store_true', help='Overwrite the existing master file')
    args = parser.parse_args()

    master_config_path = args.master_config
    child_config_path = args.child_config
    operation = args.operation
    overwrite = args.overwrite

    master_config = None
    child_config = None

    try:
        # Create config objects
        master_config = SheetConfig(master_config_path)
        child_config = SheetConfig(child_config_path)

    except SheetConfigException as e:
        print('Failed to load configurations. Error: {}'.format(e))
        traceback.print_exc()

    try:
        # Create sheet manager object
        manager = SheetManager(master_config=master_config, child_config=child_config)

        # Perform the requested operation
        if operation == 'merge':
            manager.merge()
        elif operation == 'prune':
            manager.prune()
        else:
            parser.print_help()
            raise SheetManagerException('Operation \'{}\' is not supported')

        # new_file_path = manager.create_new_filename(path_prefix=master_config.location, overwrite_existing=overwrite)
        # updated_data.to_csv(new_file_path)
        # print('Updated data saved to: {}'.format(new_file_path))

    except Exception as error:
        print('Sheet management failed. Error: {}'.format(error))
        traceback.print_exc()
