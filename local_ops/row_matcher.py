import os
from argparse import ArgumentParser


def generate_rows_from_file(input_file):
    file_path = os.path.expanduser(input_file)
    with open(file_path, 'r') as f:
        for row in f.readlines():
            yield row.strip()


def normalize_row_text(row_content):
    """
    Aims to normalize phone numbers and email addresses for better matching
    :param row_content: Raw line of text
    :return: Normalized line of text
    """

    remove_characters = {'(', ')', '-', ' '}

    for char in remove_characters:
        if char in row_content:
            row_content = row_content.replace(char, '')

    row_content = row_content.lower().strip()
    return row_content


def main(master_file, search_file, output_file, fuzzy_match=False):
    """
    Match rows in a given file with rows from another.

    :param master_file: File containing rows to flag as matched or not
    :param search_file: File containing all rows to search against the master_file
    :param output_file: File to write results to
    :param fuzzy_match: Allows for substring matches
    :return: An output file with the same number of rows as the master_file, but marked True or False for positive match
    """

    total_master_rows = 0
    total_matched_rows = 0

    out_path = os.path.expanduser(output_file)
    with open(out_path, 'w') as f:
        for master_row in generate_rows_from_file(master_file):
            total_master_rows += 1
            matched = False

            master_row = normalize_row_text(master_row)

            if master_row == '':
                f.write('False\n')
                continue

            for search_row in generate_rows_from_file(search_file):
                search_row = normalize_row_text(search_row)
                if fuzzy_match and search_row in master_row:
                    matched = True
                    break
                elif search_row == master_row:
                    matched = True
                    break
            if matched:
                f.write('True\n')
                total_matched_rows += 1
                print('Matched: {}'.format(master_row))
            else:
                f.write('False\n')

    print('-------------------')
    print('Results saved to:   {}'.format(out_path))
    print('Total rows checked: {}'.format(total_master_rows))
    print('Total rows matched: {}'.format(total_matched_rows))


if __name__ == '__main__':
    arg_parser = ArgumentParser('Match rows in a given file with rows from another.')
    arg_parser.add_argument('--master-file', '-m', required=True,
                            help='File containing rows to flag as matched or not')
    arg_parser.add_argument('--search-file', '-s', required=True,
                            help='File containing all rows to search against the master_file')
    arg_parser.add_argument('--output-file', '-o', required=True,
                            help='File to write results to')
    arg_parser.add_argument('--fuzzy-match', '-f', action='store_true', default=False,
                            help='Allows for substring matches')
    args = arg_parser.parse_args()

    main(master_file=args.master_file, search_file=args.search_file, output_file=args.output_file)
