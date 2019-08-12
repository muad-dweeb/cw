import traceback
from argparse import ArgumentParser

from SheetConfig import SheetConfig, SheetConfigException
from SheetManager import SheetManager, SheetManagerException

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--master-config', required=True, help='Path to the master sheet')
    parser.add_argument('--child-config',  required=True, help='Path to sheet to use for operating on the master sheet')
    parser.add_argument('--operation',     required=True, help='Operation to perform', choices={'merge', 'prune'})
    parser.add_argument('--overwrite',     default=False, action='store_true', help='Overwrite the existing master file')
    args = parser.parse_args()

    master_config_path = args.master_config
    child_config_path = args.child_config
    operation = args.operation
    overwrite = args.overwrite

    master_config = None
    child_config = None

    try:
        # Create config objects
        master_config = SheetConfig(master_config_path)
        child_config = SheetConfig(child_config_path)

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