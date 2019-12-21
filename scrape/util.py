import json
import os
import random
import time

from exceptions import ScraperException


def random_sleep(range_tuple, verbose=False):
    wait_time = random.uniform(*range_tuple)
    if verbose:
        print('Waiting for {} seconds...'.format(round(wait_time, 2)))
    time.sleep(wait_time)


def get_config(config_path):
    required_keys = {'email', 'pass'}
    config_path = os.path.expanduser(config_path)

    if not os.path.isfile(config_path):
        raise ScraperException('Config is not a valid file: {}'.format(config_path))

    try:
        with open(config_path, 'r') as f:
            config_dict = json.loads(f.read())
    except (OSError, ValueError) as e:
        raise ScraperException('Unable to load JSON from file: {}. Error: {}'.format(config_path, e))

    for key in required_keys:
        if key not in config_dict.keys():
            raise ScraperException('Config is missing required key: {}'.format(key))

    print('Config successfully loaded from: {}'.format(config_path))
    return config_dict
