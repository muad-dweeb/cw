import os
import time
from argparse import ArgumentParser


def main(input_file_path, number_to_keep):
    start = time.time()
    root, ext = os.path.splitext(input_file_path)
    output_file = '{}_trimmed{}'.format(root, ext)
    output_lines = list()

    with open(os.path.expanduser(input_file_path), 'r') as f:
        lines = f.readlines()

    for line in lines:
        if line == '\n':
            output_lines.append(line)
            continue
        first_twenty_elements = line.strip('\n').split('\t')[0:number_to_keep]
        line = '\t'.join(first_twenty_elements) + '\n'
        output_lines.append(line)

    with open(os.path.expanduser(output_file), 'w') as f:
        f.writelines(output_lines)

    elapsed = time.time() - start
    print('Trim complete in {} seconds.'.format(elapsed))


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--tsv-path', required=True)
    parser.add_argument('-n', '--number-to-keep', type=int, default=100, required=False)
    args = parser.parse_args()

    main(input_file_path=args.tsv_path, number_to_keep=args.number_to_keep)
