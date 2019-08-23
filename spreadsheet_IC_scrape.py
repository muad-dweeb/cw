from selenium.common.exceptions import NoSuchWindowException

from ICScraper import ICScraper
from exceptions import ScraperException

if __name__ == '__main__':

    scraper = None
    try:
        scraper = ICScraper()
        scraper.manual_login()

        # TESTING
        contact_info = scraper.get_all_info('andrew', 'galloway', 'seattle', 'wa')
        print(contact_info)

    except ScraperException as e:
        print('Scrape failed. Error: {}'.format(e))

    except NoSuchWindowException:
        print('Window was closed prematurely')

    if scraper:
        scraper.close()
