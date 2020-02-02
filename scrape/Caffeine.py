import subprocess

from scrape.util import is_darwin


class Caffeine:
    """
    Simple wrapper for modern MacOS built-in 'caffeinate' command
    """

    # https://stackoverflow.com/a/29603792/3900915

    def __init__(self):
        pass

    @staticmethod
    def start(pid):
        if is_darwin():
            subprocess.Popen(['caffeinate', '-w', str(pid)])
        else:
            raise NotImplementedError('Caffeine is currently only implemented for Mac :(')

    def stop(self):
        pass
