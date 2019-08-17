import json
import os

from exceptions import SheetConfigException


class SheetConfig(object):
    def __init__(self, config_name):

        # Assemble the config file path
        config_name = os.path.splitext(config_name)[0]
        config_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config')
        self.config_file = os.path.join(config_dir, config_name) + '.json'

        if not os.path.isfile(self.config_file):
            raise SheetConfigException('File does not exist: {}'.format(self.config_file))
        else:
            print('Loading config: {}'.format(self.config_file))

        required_keys = {'location', 'id_column', 'id_char_count'}

        try:
            with open(self.config_file, 'r') as f:
                config_dict = json.load(f)
        except Exception as e:
            raise SheetConfigException('Unable to read JSON from file: {}. '
                                       'Error: {}'.format(self.config_file, e))

        for key in required_keys:
            if key not in config_dict.keys():
                raise SheetConfigException('Required key \'{}\' missing from '
                                           'config JSON: {}'.format(key, config_dict))

        self.location = config_dict['location']
        self.id_column = config_dict['id_column']
        self.id_char_count = config_dict['id_char_count']

        # Validate id char count
        if self.id_char_count != 'mixed' and type(self.id_char_count) != int:
            try:
                self.id_char_count = int(self.id_char_count)
            except ValueError:
                raise SheetConfigException('Unable to coerce id_char_count \'{}\' to an integer.')