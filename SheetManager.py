import csv

from copy import deepcopy
from datetime import datetime
from os import path

from exceptions import SheetManagerException

SEP = '-' * 70


class SheetManager(object):

    def __init__(self, master_config, child_config, overwrite=False, verbose=False):

        self.verbose = verbose

        # These are SheetConfig objects
        self._master_config = master_config
        self._child_config = child_config

        out_file = self.create_new_filename(in_path=self._master_config.location,
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
        aligned_count = 0

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
        print('    Child rows with proper ID lengths: {}'.format(len(remaining_child_rows)))
        print('    Child rows with incorrect ID lengths: {}'.format(len(unwanted_child_ids)))
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
                    n_child_id = self._normalize_uid(uid=child_id)
                    n_master_id = self._normalize_uid(uid=master_id, actual_id_len=self._master_config.id_char_count)
                    if n_child_id == n_master_id:
                        aligned_count += 1
                        if self.verbose:
                            print('    ID match: {}'.format(master_id))

                        # Add all children values to out_dict
                        for c_key, c_value in c_row.iteritems():
                            out_dict[c_key] = c_value

                        # Delete child from remaining children so it is never iterated over again
                        remaining_child_rows.remove(c_row)

                # Write completed out_dict to the output CSV file
                output_writer.writerow(out_dict)

            print('Rows aligned by {}: {}'.format(self._master_config.id_column, aligned_count))

            # Don't forget the orphan children!
            print('Unmatched child rows appended to the end of the file: {}'.format(len(remaining_child_rows)))
            for o_row in remaining_child_rows:
                output_writer.writerow(o_row)

        # Display unmatched child IDs for verification
        if self.verbose:
            print(SEP)
            print('Child rows skipped due to ID length mismatch:')
            for c_id in unwanted_child_ids:
                print('    {}'.format(c_id))

    def prune(self):
        raise SheetManagerException('prune method not yet implemented')

    @staticmethod
    def _normalize_uid(uid, actual_id_len=None):
        """ Delete hyphens and spaces from input string and add missing leading zeros """
        uid = uid.replace('-', '').replace(' ', '')
        while actual_id_len is not None and len(uid) < actual_id_len:
            uid = '0' + uid
        return uid

    @staticmethod
    def create_new_filename(in_path, overwrite_existing=False):
        """ Save to a new CSV file with an incrementing filename unless overwrite is requested """
        # YYYYMMDD
        now_string = datetime.now().strftime('%Y%m%d')

        full_path = path.expanduser(in_path)

        # Remove any file extension from the path
        full_path = path.splitext(full_path)[0]

        out_path = '{}_{}.csv'.format(full_path, now_string)

        if not overwrite_existing:
            increment = 1
            while path.isfile(out_path):
                out_path = '{}_{}_{}.csv'.format(full_path, now_string, increment)
                increment += 1

        return out_path
