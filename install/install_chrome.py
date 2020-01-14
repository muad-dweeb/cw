from exceptions import InstallerException
from install.ChromeInstaller import ChromeInstaller
from lib.util import create_logger


def install_chrome(debug=False):
    logger = create_logger(caller=__file__, debug=debug)
    try:
        installer = ChromeInstaller()
        logger.info('Getting Chrome version: {}'.format(installer.version))
        logger.info('Downloading and installing browser...')
        installer.download_and_install_browser()
        logger.info('On OSX, drag the browser icon into the Application folder using the popup.')
        logger.info('Downloading and unpacking driver...')
        installer.download_driver()
    except InstallerException as e:
        logger.exception('Installation failed: {}'.format(e))


if __name__ == '__main__':
    install_chrome()
