import json
from os import path


class RunConfig(object):

    CONFIG_PATH = path.join(path.dirname(path.dirname(path.abspath(__file__))), 'config', 'scrape_run_config.json')
    REQUIRED_KEYS = {'sites', 'upload_bucket', 'email'}

    def __init__(self, site_key):

        self._site_key = site_key

        self.wait_range_between_rows = 0
        self.wait_range_between_report_loads = 0
        self.upload_bucket = None
        self.email_sender = None
        self.email_recipient = None

        self._load_config_json()

    def _load_config_json(self):
        with open(RunConfig.CONFIG_PATH, 'r') as config:
            config_dict = json.loads(config.read())

            for key in RunConfig.REQUIRED_KEYS:
                if key not in config_dict.keys():
                    raise KeyError('Required key \'{}\' missing from config file: {}'.format(key,
                                                                                             RunConfig.CONFIG_PATH))

            if self._site_key not in config_dict['sites'].keys():
                raise KeyError('Site key \'{}\' missing from config file: {}'.format(self._site_key,
                                                                                     RunConfig.CONFIG_PATH))

            self.wait_range_between_rows = config_dict['sites'][self._site_key]['wait_range_between_rows']
            self.wait_range_between_report_loads = config_dict['sites'][self._site_key]['wait_range_between_report_loads']
            self.upload_bucket = config_dict['upload_bucket']
            self.email_sender = config_dict['email']['sender']
            self.email_recipient = config_dict['email']['recipient']
