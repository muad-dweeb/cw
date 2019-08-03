import argparse
import os
import pandas


class SheetManagerException(BaseException):
    pass


class SheetManager(object):

    def __init__(self, master_file, child_file, match_column):
        self.match_column = match_column

        # Required files
        master_path = os.path.expanduser(master_file)
        child_path = os.path.expanduser(child_file)

        # Existence validation
        for f in {master_path, child_path}:
            if os.path.isfile(f):
                print('Found file: {}'.format(f))
            else:
                raise SheetManagerException('{} is not a file.'.format(f))

        self.master = pandas.read_csv(master_path)
        self.child = pandas.read_csv(child_path)

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
        return uid.replace('-', ' ')

    @staticmethod
    def __validate_uniqueness(some_list):
        if len(some_list) != len(set(some_list)):
            return False
        return True


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

    except SheetManagerException as e:
        print('Sheet management failed. Error: {}'.format(e))