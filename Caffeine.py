import subprocess
import sys


class Caffeine:
    """
    Simple wrapper for modern MacOS built-in 'caffeinate' command
    """

    # https://stackoverflow.com/a/29603792/3900915

    def __init__(self):
        pass

    @staticmethod
    def _is_darwin():
        if 'darwin' in sys.platform:
            return True
        else:
            return False

    def start(self, pid):
        if self._is_darwin():
            subprocess.Popen(['caffeinate', '-w', str(pid)])

    def stop(self):
        pass
