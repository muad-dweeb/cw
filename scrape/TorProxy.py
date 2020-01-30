import re
import subprocess

from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium import webdriver

from lib.exceptions import TorProxyException
from scrape.util import is_darwin

"""
https://daoyuan.li/configure-selenium-and-chrome-to-use-tor-proxy/

SETUP

    brew install tor
    brew install privoxy
    
    Configure privoxy (vi /usr/local/etc/privoxy/config) to chain it with Tor:
    
        forward-socks5t   /               127.0.0.1:9050 .

"""


def check_ip(driver):
    url = 'http://httpbin.org/ip'
    driver.get(url)

    if '"origin"' not in driver.page_source:
        raise TorProxyException('IP check page load failed')

    ip_match = re.findall(pattern='(\\d+\\..+\\.\\d+)', string=driver.page_source)
    if len(ip_match) > 0:
        ip = ip_match[0]
    else:
        raise TorProxyException('No IP address parsed from page: {}'.format(url))

    return ip


class TorProxy(Proxy):
    def __init__(self):
        super().__init__()
        self.proxy_type = ProxyType.MANUAL
        self.http_proxy = "http://localhost:8118"
        self.ssl_proxy = "http://localhost:8118"

        self.capabilities = webdriver.DesiredCapabilities.CHROME
        self.add_to_capabilities(self.capabilities)

    @staticmethod
    def _start_tor():
        if is_darwin():
            subprocess.run('brew services restart tor', shell=True)
        else:
            raise NotImplementedError('TorProxy currently only implemented for Mac :(')

    @staticmethod
    def _stop_tor():
        if is_darwin():
            subprocess.run('brew services stop tor', shell=True)
        else:
            raise NotImplementedError('TorProxy currently only implemented for Mac :(')

    @staticmethod
    def _start_privoxy():
        """ Start privoxy by default on port 8118 """
        if is_darwin():
            subprocess.run('brew services restart privoxy', shell=True)
        else:
            raise NotImplementedError('TorProxy currently only implemented for Mac :(')

    @staticmethod
    def _stop_privoxy():
        if is_darwin():
            subprocess.run('brew services stop privoxy', shell=True)
        else:
            raise NotImplementedError('TorProxy currently only implemented for Mac :(')

    def start(self):
        self._start_tor()
        self._start_privoxy()

    def stop(self):
        self._stop_privoxy()
        self._stop_tor()


def test_tor_proxy():

    options = webdriver.ChromeOptions()
    # options.add_argument('headless')
    options.add_argument("--window-size=420,420")

    # Without proxy
    driver = webdriver.Chrome(options=options)
    normal_ip = check_ip(driver)
    driver.close()
    print('Normal IP: {}'.format(normal_ip))

    # With proxy
    proxy = TorProxy()
    proxy.start()
    driver = webdriver.Chrome(options=options, desired_capabilities=proxy.capabilities)
    proxy_ip = check_ip(driver)
    driver.close()
    print('Proxy IP: {}'.format(proxy_ip))
    proxy.stop()

    if normal_ip == proxy_ip:
        print('Test failed!')
    else:
        print('Test succeeded!')


if __name__ == '__main__':
    test_tor_proxy()
