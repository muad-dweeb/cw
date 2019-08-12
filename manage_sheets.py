import traceback
from argparse import ArgumentParser
import time

from SheetConfig import SheetConfig, SheetConfigException
from SheetManager import SheetManager, SheetManagerException

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--master-config', required=True, help='Master config name')
    parser.add_argument('--child-config',  required=True, help='Child config name')
    parser.add_argument('--operation',     required=True, help='Operation to perform', choices={'merge', 'prune'})
    parser.add_argument('--overwrite',     default=False, action='store_true', help='Overwrite the existing master file')
    parser.add_argument('--verbose', '-v', default=False, action='store_true', help='Display more detailed information')
    args = parser.parse_args()

    master_config_name = args.master_config
    child_config_name = args.child_config
    operation = args.operation
    overwrite = args.overwrite
    verbose = args.verbose

    master_config = None
    child_config = None

    start = time.time()

    try:
        # Create config objects
        master_config = SheetConfig(master_config_name)
        child_config = SheetConfig(child_config_name)

    except SheetConfigException as e:
        print('Failed to load configurations. Error: {}'.format(e))
        traceback.print_exc()

    try:
        # Create sheet manager object
        manager = SheetManager(master_config=master_config, child_config=child_config)

        # Perform the requested operation
        if operation == 'merge':
            manager.merge()
        elif operation == 'prune':
            manager.prune()
        else:
            parser.print_help()
            raise SheetManagerException('Operation \'{}\' is not supported')

    except Exception as error:
        print('Sheet management failed. Error: {}'.format(error))
        traceback.print_exc()

    end = time.time()
    elapsed = time.strftime('%H:%M:%S', time.gmtime(end - start))
    print('=' * 70)
    print('Total run time: {}'.format(elapsed))
