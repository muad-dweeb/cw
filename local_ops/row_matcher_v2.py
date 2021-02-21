import os
from argparse import ArgumentParser
from csv import DictReader


# Broker Match Sheet to Master File mapping
mapping = {
    'Office Phone': ['Owner1 Phone Master', 'Owner2 Phone Master'],
    'Cell Phone': ['Owner1 Phone Master', 'Owner2 Phone Master'],
    'Email': ['Owner1 Email Master', 'Owner2 Email Master']
}


def normalize_cell_text(cell_content):
    """
    Aims to normalize phone numbers and email addresses for better matching
    :param cell_content: Raw string
    :return: Normalized string
    """

    remove_characters = {'(', ')', '-', ' '}

    for char in remove_characters:
        if char in cell_content:
            cell_content = cell_content.replace(char, '')

    cell_content = cell_content.lower().strip()
    return cell_content


def match_rows(broker_file, master_file, output_file):
    total_master_rows = 0
    total_matched_rows = 0

    broker_path = os.path.expanduser(broker_file)
    master_path = os.path.expanduser(master_file)
    out_path = os.path.expanduser(output_file)

    # These are dangerous memory-wise
    with open(broker_path, 'r') as b:
        broker_info = list(DictReader(b))

    with open(master_path, 'r') as m:
        master_info = list(DictReader(m, delimiter='\t'))

    # I despise this amount of nesting
    with open(out_path, 'w') as f:
        for master_row in master_info:
            total_master_rows += 1
            matched = False

            for broker_row in broker_info:
                if matched:
                    break

                for broker_key, mapped_columns in mapping.items():
                    if broker_row[broker_key] == '':
                        continue
                    for column in mapped_columns:
                        if column not in master_row.keys():
                            continue
                        normalized_broker_value = normalize_cell_text(broker_row[broker_key])
                        normalized_master_value = normalize_cell_text(master_row[column])
                        if normalized_broker_value in normalized_master_value.split(','):
                            matched = True
                            print('Row {} Matched: {}'.format(total_master_rows + 1, broker_row[broker_key]))
                            break

                if matched:
                    f.write('True\n')
                    total_matched_rows += 1
                    continue
                else:
                    f.write('False\n')

    print('-------------------')
    print('Results saved to:   {}'.format(out_path))
    print('Total rows checked: {}'.format(total_master_rows))
    print('Total rows matched: {}'.format(total_matched_rows))


if __name__ == '__main__':
    arg_parser = ArgumentParser('Match rows in a given file with rows from another using multiple cells.')
    arg_parser.add_argument('--broker', '-b', required=True,
                            help='File containing broker contact info rows to search against the master_file')
    arg_parser.add_argument('--master', '-m', required=True,
                            help='File containing rows to flag as matched or not')
    arg_parser.add_argument('--output', '-o', required=True,
                            help='File to write results to')
    args = arg_parser.parse_args()
    match_rows(broker_file=args.broker,
               master_file=args.master,
               output_file=args.output)
