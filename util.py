from datetime import datetime
from os import path


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