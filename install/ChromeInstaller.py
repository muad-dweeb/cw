import subprocess
import urllib.request
import zipfile
from os import path, mkdir

import requests

from exceptions import InstallerException
from scrape.util import is_darwin, is_linux


class ChromeInstaller(object):
    def __init__(self):
        self.version = self._get_chrome_latest_release()
        self.browser_url = self._set_browser_url()
        self._lib_dir = path.join(path.dirname(path.dirname(__file__)), 'lib')

    #############
    #   Setup   #
    #############

    @staticmethod
    def _set_browser_url():
        if is_darwin():
            return 'https://dl.google.com/chrome/mac/stable/GGRO/googlechrome.dmg',
        elif is_linux():
            return 'https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb'
        else:
            raise InstallerException('Unsupported OS')

    def _create_lib_dir(self):
        if not path.isdir(self._lib_dir):
            mkdir(self._lib_dir)

    #############
    #  Browser  #
    #############

    def download_and_install_browser(self):
        """ download the latest chrome browser installer """
        installer_file_name = path.basename(self.browser_url)
        local_installer_path = path.join(self._lib_dir, installer_file_name)

        # Download
        urllib.request.urlretrieve(self.browser_url, local_installer_path)

        # Install
        if is_darwin():
            self._install_browser_mac(local_installer_path)
        elif is_linux():
            self._install_browser_linux(local_installer_path)
        else:
            raise InstallerException('Unsupported OS')

    @staticmethod
    def _install_browser_mac(installer_path):
        """
        untested!
        https://superuser.com/q/602680
        """
        mount_location = '/Volumes/Google\\ Chrome/Google\\ Chrome.app'

        # Open installer
        subprocess.run(['open', installer_path])

        # Move to Applications
        subprocess.run(['sudo', 'cp', '-r', mount_location, '/Applications/'])

    @staticmethod
    def _install_browser_linux(installer_path):
        """
        https://linoxide.com/linux-how-to/install-latest-chrome-run-terminal-ubuntu/
        """

        subprocess.run(['sudo', 'dpkg', '-i', installer_path])
        subprocess.run(['sudo', 'apt-get', 'install', '-f'])

    ############
    #  Driver  #
    ############

    def download_driver(self):
        """ download the latest chromedriver version """
        base_url = 'https://chromedriver.storage.googleapis.com/{}'.format(self.version)
        if is_darwin():
            file_name = 'chromedriver_mac64.zip'
        elif is_linux():
            file_name = 'chromedriver_linux64.zip'
        else:
            raise InstallerException('Unsupported OS')

        url = path.join(base_url, file_name)
        local_package_path = path.join(self._lib_dir, file_name)

        # Download
        urllib.request.urlretrieve(url, local_package_path)

        # Unpack
        with zipfile.ZipFile(local_package_path, 'r') as package:
            package.extractall(self._lib_dir)

        # Congrats, it's a shiny new chromedriver!
        driver_path = path.join(path.dirname(local_package_path), 'chromedriver')

        # Python zipfile unpacks without preserving the intended permissions, so set those here
        subprocess.run(['chmod', '755', driver_path])

        return driver_path

    @staticmethod
    def _get_chrome_latest_release():
        url = "https://chromedriver.storage.googleapis.com/LATEST_RELEASE"
        response = requests.request("GET", url)
        return response.text
