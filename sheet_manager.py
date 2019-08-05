import argparse
import os
from datetime import datetime

import pandas


class SheetManagerException(BaseException):
    pass


class SheetManager(object):

    def __init__(self, master_file, child_file, match_column):
        self.match_column = match_column

        # Required files
        self.master_path = os.path.expanduser(master_file)
        self.child_path = os.path.expanduser(child_file)

        # Existence validation
        for f in {self.master_path, self.child_path}:
            if os.path.isfile(f):
                print('Found file: {}'.format(f))
            else:
                raise SheetManagerException('{} is not a file.'.format(f))

        self.master = pandas.read_csv(self.master_path)
        self.child = pandas.read_csv(self.child_path)

    def merge(self):
        """ Merge child into master using match_column """

        # with open(self.master_file) as mf:
        #     reader = csv.reader(mf, delimiter=',')
        #     line_count = 0
        #     for row in reader:
        #         if line_count == 0:
        #             # TODO: untested
        #             print('Master headers: {}'.format(', '.join(row)))
        #             # TODO: make sure row is an iterable
        #             if self.match_column not in row:
        #                 raise SheetManagerException('Expected column name \'{}\' not found.')'
        #         else:
        #             WAIT. hold up...

        # TODO: Will need to define a column-mapping config so columns don't duplicate
        merged = self.master.merge(self.child, on=self.match_column)
        return merged

    def prune(self):
        raise SheetManagerException('prune method not yet implemented')

    @staticmethod
    def __normalize_uid(uid):
        """ Normalize the discrepancies in UIDs from different source sheets for easier comparison """
        return uid.replace('-', ' ')

    @staticmethod
    def __validate_uniqueness(some_list):
        """ Use this to validate UID columns """
        if len(some_list) != len(set(some_list)):
            return False
        return True

    @staticmethod
    def __save_new_csv(path_prefix, file_contents, overwrite=False):
        """ Save to a new CSV file with an incrementing filename unless overwrite is requested """
        # YYYYMMDD
        now_string = datetime.now().strftime('%Y%m%d')
        # Remove any file extension from the path
        path_prefix = os.path.splitext(path_prefix)[0]
        full_path = '{}_{}.csv'.format(path_prefix, now_string)

        if not overwrite:
            increment = 1
            while os.path.isfile(full_path):
                full_path = '{}_{}_{}.csv'.format(path_prefix, now_string, increment)
                increment += 1

        try:
            with open(full_path, 'w') as f:
                f.write(file_contents)
            print('File saved to: {}'.format(full_path))
        except IOError as e:
            raise SheetManagerException('Failed to save file: {} Error: {}'.format(full_path, e))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--master',       required=True, help='Path to the master sheet')
    parser.add_argument('--child',        required=True, help='Path to sheet to use for operating on the master sheet')
    parser.add_argument('--match-column', required=True, help='Column name to join sheets with')
    parser.add_argument('--operation',    required=True, help='Operation to perform', choices={'merge', 'prune'})
    args = parser.parse_args()

    master = args.master
    child = args.child
    operation = args.operation
    match_column = args.match_column

    try:
        manager = SheetManager(master_file=master, child_file=child, match_column=match_column)

        if operation == 'merge':
            manager.merge()
        elif operation == 'prune':
            manager.prune()
        else:
            print('Operation \'{}\' is not supported')

    except SheetManagerException as error:
        print('Sheet management failed. Error: {}'.format(error))
