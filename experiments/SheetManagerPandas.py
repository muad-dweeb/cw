from datetime import datetime
from os import path

import pandas

from SheetManager import SheetManagerException


"""
Attempting to use pandas for faster, more efficient merging.
Maybe not worth it?
"""


class SheetManagerPandas(object):

    def __init__(self, master_config, child_config):
        self._master_config = master_config
        self._child_config = child_config

        # Required files
        self._master_csv_path = path.expanduser(self._master_config.location)
        self._child_csv_path = path.expanduser(self._child_config.location)

        # Sheet Existence validation
        for f in {self._master_csv_path, self._child_csv_path}:
            if path.isfile(f):
                print('Found file: {}'.format(f))
            else:
                raise SheetManagerException('{} is not a file.'.format(f))

        # Ingest the data
        self.master = pandas.read_csv(self._master_csv_path, index_col=self._master_config.id_column)
        self.child = pandas.read_csv(self._child_csv_path)

        # Normalize the values in the id columns
        self.__normalize_uid(self.master, self._master_config.id_column)
        self.__normalize_uid(self.child, self._child_config.id_column)

    def merge(self):
        """ Merge child into master using match_column """

        dup_col_suffix = '__y'

        merged = self.master.merge(self.child,
                                   how='outer',
                                   left_index=True,
                                   right_on=self._child_config.id_column,
                                   suffixes=('', dup_col_suffix))

        # Clean up duplicate columns
        for index, row in merged.iterrows():
            for col in merged.columns:
                if not col.endswith(dup_col_suffix):
                    continue
                x = merged.loc[index, col.strip(dup_col_suffix)]
                y = merged.loc[index, col]
                # SKip NaN values
                if type(x) != str or type(y) != str:
                    continue
                if x.lower() == y.lower():
                    merged.loc[index, col] = pandas.np.nan

        return merged

    def prune(self):
        raise SheetManagerException('prune method not yet implemented')

    @staticmethod
    def __normalize_uid(data_frame, column_name):
        """ Normalize the discrepancies in UIDs from different source sheets for easier comparison """
        for index, row in data_frame.iterrows():
            if column_name in data_frame.columns:
                uid_in = data_frame.loc[index, column_name]
                uid_out = uid_in.replace('-', ' ')
                data_frame.loc[index, column_name] = uid_out
            else:
                uid_in = data_frame.loc[index]
                uid_out = uid_in.replace('-', ' ')
                data_frame.loc[index] = uid_out

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
