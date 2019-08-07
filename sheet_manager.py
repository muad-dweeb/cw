from argparse import ArgumentParser
from os import path
from datetime import datetime

import pandas


class SheetManagerException(BaseException):
    pass


class SheetManager(object):

    def __init__(self, master_file, child_file, match_column):
        self.match_column = match_column

        # Required files
        self.master_path = path.expanduser(master_file)
        self.child_path = path.expanduser(child_file)

        # Existence validation
        for f in {self.master_path, self.child_path}:
            if path.isfile(f):
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
        merged = self.master.merge(self.child, how='outer', on=self.match_column, suffixes=('', '__y'))
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
    def create_new_filename(path_prefix, overwrite_existing=False):
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


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--master',       required=True, help='Path to the master sheet')
    parser.add_argument('--child',        required=True, help='Path to sheet to use for operating on the master sheet')
    parser.add_argument('--match-column', required=True, help='Column name to join sheets with')
    parser.add_argument('--operation',    required=True, help='Operation to perform', choices={'merge', 'prune'})
    parser.add_argument('--overwrite',    default=False, action='store_true', help='Overwrite the existing master file')
    args = parser.parse_args()

    master = args.master
    child = args.child
    match_column = args.match_column
    operation = args.operation
    overwrite = args.overwrite

    try:
        manager = SheetManager(master_file=master, child_file=child, match_column=match_column)

        if operation == 'merge':
            updated_data = manager.merge()
        elif operation == 'prune':
            updated_data = manager.prune()
        else:
            parser.print_help()
            raise SheetManagerException('Operation \'{}\' is not supported')

        new_file_path = manager.create_new_filename(path_prefix=manager.master_path, overwrite_existing=overwrite)
        updated_data.to_csv(new_file_path)

    except Exception as error:
        print('Sheet management failed. Error: {}'.format(error))
