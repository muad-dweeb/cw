import json
import os


class SheetConfig(object):
    def __init__(self, file_path):

        self.config_file = os.path.expanduser(file_path)
        if not os.path.isfile(self.config_file):
            raise OSError('File does not exist: {}'.format(self.config_file))

        self.location = None
        self.id_column = None
        self.id_char_count = None

        self._get_config()

        # TODO: Validate values here?

    def _get_config(self):

        required_keys = {'location', 'id_column', 'id_char_count'}

        try:
            with open(self.config_file, 'r') as f:
                config_dict = json.load(f)
        except Exception as e:
            raise IOError('Unable to read JSON from file: {}. '
                          'Error: {}'.format(self.config_file, e))

        for key in required_keys:
            if key not in config_dict.keys():
                raise KeyError('Required key \'{}\' missing from '
                               'config JSON: {}'.format(key, config_dict))

        self.location = config_dict['location']
        self.id_column = config_dict['id_column']
        self.id_char_count = config_dict['id_char_count']
