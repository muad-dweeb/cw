import csv

from copy import deepcopy
from os import path

from lib.exceptions import SheetManagerException
from lib.util import create_new_filename

SEP = '-' * 70


class SheetManager(object):

    def __init__(self, master_config, child_config, overwrite=False, verbose=False):

        self.verbose = verbose

        # These are SheetConfig objects
        self._master_config = master_config
        self._child_config = child_config

        out_file = create_new_filename(in_path=self._master_config.location,
                                       overwrite_existing=overwrite)
        self.out_file = path.expanduser(out_file)

        # Required files
        self._master_csv_path = path.expanduser(self._master_config.location)
        self._child_csv_path = path.expanduser(self._child_config.location)

        # Sheet Existence validation
        for f in {self._master_csv_path, self._child_csv_path}:
            if path.isfile(f):
                print('Found file: {}'.format(f))
            else:
                raise SheetManagerException('{} is not a file.'.format(f))

        self.master_reader = self._initialize_csv_reader(self._master_csv_path)
        self.child_reader = self._initialize_csv_reader(self._child_csv_path)
        self.child_reader.fieldnames = self._make_child_fieldnames_unique()

    @staticmethod
    def _initialize_csv_reader(file_path):
        return csv.DictReader(open(file_path))

    def _make_child_fieldnames_unique(self):
        """ Disallows duplicate column headers between Master and Child by adding a suffix where needed """
        unique_fieldnames = list()
        for name in self.child_reader.fieldnames:
            if name in self.master_reader.fieldnames and name != self._child_config.id_column:
                name += '__1'
            unique_fieldnames.append(name)
        return unique_fieldnames

    def merge(self):
        """
        Merge child into master using match_column

        The mental gymnastics here broke my fucking brain.
        """

        output_fieldnames = self.master_reader.fieldnames + self.child_reader.fieldnames

        unwanted_child_ids = list()

        finished = False
        while not finished:

            # This is a flag that instructs nested loops to break one after the other. Very ugly. Do not like.
            start_over = False

            # Reset everything every time this loop is kicked off for a fresh start
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

            with open(self.out_file, 'w') as out:
                print('Writing out to: {}'.format(self.out_file))
                output_writer = csv.DictWriter(out, output_fieldnames)

                # Initialize output CSV
                output_writer.writeheader()

                # Iterate through master rows
                for m_row in self.master_reader:

                    if start_over:
                        break

                    out_dict = deepcopy(m_row)
                    # Pre-initialize out_dict with the most up-to-date output_fieldnames
                    for name in output_fieldnames:
                        if name not in out_dict.keys():
                            out_dict[name] = ''

                    master_id = m_row[self._master_config.id_column]

                    # Iterate through remaining children
                    for c_row in remaining_child_rows:

                        if start_over:
                            break

                        child_id = c_row[self._child_config.id_column]

                        # Do the IDs match after normalization?
                        n_child_id = self._normalize_uid(uid=child_id)
                        n_master_id = self._normalize_uid(uid=master_id, actual_id_len=self._master_config.id_char_count)
                        if n_child_id == n_master_id:
                            aligned_count += 1
                            if self.verbose:
                                print('    ID match: {}'.format(master_id))

                            # Add all children values to out_dict
                            for c_key, c_value in c_row.items():

                                if start_over:
                                    break

                                # TODO: The following while loop and the if statement immediately after may be able to
                                #   be consolidated into one, but I'm not screwing around with it right now.

                                # Don't override existing information!
                                while c_key in m_row.keys():
                                    if c_key == self._child_config.id_column:
                                        break
                                    else:
                                        c_key = self.__increment_key(c_key)

                                    # Missing key means the dictWriter must be re-initialized with the key added.
                                    if c_key not in output_fieldnames:
                                        if self.verbose:
                                            print('    Key \'{}\' missing from Master. '
                                                  'Adding and starting over...'.format(c_key))
                                        output_fieldnames.append(c_key)
                                        start_over = True
                                        break

                                # More than one child found for master row?
                                if c_key in out_dict.keys() and c_key != self._child_config.id_column and len(out_dict[c_key]) > 0:

                                    # Increment everything!
                                    inserted = False
                                    while c_key in out_dict.keys():
                                        c_key = self.__increment_key(c_key)

                                        # Found an empty, incremented cell...
                                        if c_key in out_dict.keys() and len(out_dict[c_key]) == 0:

                                            # Put it in there!
                                            out_dict[c_key] = c_value
                                            inserted = True
                                            break

                                    # Not being able to insert the value implies that the key needs to be added to
                                    #   the dictWriter for re-initialization.
                                    if not inserted:
                                        if self.verbose:
                                            print('    Adding key \'{}\' and starting over...'.format(c_key))
                                        output_fieldnames.append(c_key)
                                        start_over = True
                                        break

                                # Didn't encounter any of that nonsense above? Nice. Just shove it right in.
                                out_dict[c_key] = c_value

                            # Delete child from remaining children so it is never iterated over again
                            remaining_child_rows.remove(c_row)

                    # Write completed out_dict to the output CSV file
                    output_writer.writerow(out_dict)

                if start_over:
                    if self.verbose:
                        print('Re-initializing readers...')
                    self.master_reader = self._initialize_csv_reader(self._master_csv_path)
                    self.child_reader = self._initialize_csv_reader(self._child_csv_path)
                    continue

                print('Rows aligned by {}: {}'.format(self._master_config.id_column, aligned_count))

                # Don't forget the orphan children!
                print('Unmatched child rows appended to the end of the file: {}'.format(len(remaining_child_rows)))
                for o_row in remaining_child_rows:
                    output_writer.writerow(o_row)

                finished = True

        # Display unmatched child IDs for verification
        if self.verbose:
            print(SEP)
            print('Child rows skipped due to ID length mismatch:')
            for c_id in unwanted_child_ids:
                print('    {}'.format(c_id))

    def prune(self):
        raise SheetManagerException('prune method not yet implemented')

    @staticmethod
    def __increment_key(key_name):
        if '__' in key_name:
            prefix, increment = key_name.rsplit('__', 1)
            key_name = '{}__{}'.format(prefix, int(increment) + 1)
        else:
            key_name += '__1'
        return key_name

    @staticmethod
    def _normalize_uid(uid, actual_id_len=None):
        """ Delete hyphens and spaces from input string and add missing leading zeros """
        uid = uid.replace('-', '').replace(' ', '')
        while actual_id_len is not None and len(uid) < actual_id_len:
            uid = '0' + uid
        return uid
