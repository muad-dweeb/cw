import random
import time


def random_sleep(range_tuple):
    wait_time = random.uniform(*range_tuple)
    print('Waiting for {} seconds...'.format(round(wait_time, 2)))
    time.sleep(wait_time)
