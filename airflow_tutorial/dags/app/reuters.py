import datetime
import logging
import os
import re
import sys
import time
import uuid

import bs4
from bs4 import BeautifulSoup
from pymongo.errors import DuplicateKeyError
from dateutil import parser
sys.path.append(r'../../')

import common_methods
import nodriver as uc
from selenium.common.exceptions import InvalidSessionIdException
from bson import Binary, UuidRepresentation

BASE_URL = 'https://www.reuters.com'
CurrentDate = time.strftime('%Y-%m-%d', time.localtime(time.time()))


class IrrelevantCategoryError(Exception):
    def __init__(self, category):
        super().__init__()
        self.category = category


class Article:
    def __init__(self, url, title, category, author, date, utc_datetime, content):
        self.url = url
        self.title = title
        self.category = category
        self.author = author
        self.date = date
        self.utc_datetime = utc_datetime
        self.content = content


    def are_all_fields_present(self) -> bool:
        if not self.url:
            print(f"Missing URL")
            return False

        if not self.title:
            print(f"Missing title: {self.url}")
            return False

        if not self.category:
            print(f"Missing category: {self.title}\n{self.url}")
            return False

        if not self.author:
            print(f"Missing author: {self.title}\n{self.url}")
            return False

        if not self.date:
            print(f"Missing date: {self.title}\n{self.url}")
            return False

        if not self.utc_datetime:
            print(f"Missing UTC datetime: {self.title}\n{self.url}")
            return False

        if not self.content:
            print(f"Missing content: {self.title}\n{self.url}")
            return False

        # All fields are present
        return True

# End of Article class

async def login(browser):

    tab = await browser.get('https://www.reuters.com/')
    await tab.maximize()
    time.sleep(5)
    username = 'desktopremote891@gmail.com'
    password = 'Aidf#$123456'
    time.sleep(3)
    elem = await tab.select('#fusion-app > header > div > div > div > div > div.site-header__button-group__2OXlt > a.button__link__uTGln.button__secondary__18moI.button__round__1nYLA.button__w_auto__6WYRo.text-button__container__3q3zX.site-header__button__3fm5y > span > span')
    await elem.click()
    time.sleep(2)
    elem = await tab.select('#email')
    await elem.send_keys(username)
    elem = await tab.select('#password')
    await elem.send_keys(password)
    time.sleep(2)

    elem = await tab.select('#main-content > div > div.sign-in-page__form__3oDWj > div.card__card-wrapper__2B5Ki.sign-in-form__card-wrapper__1xqYt > div > div > div > form > button > span > span')
    await elem.click()
    print("Logging in")
    time.sleep(10)
    return browser

# Returns the date and utc datetime of a given date string
def format_date_text(date_text):
    # Remove the 'Updated ... ago' part if present
    date_time_part = date_text.split(' Updated ')[0].strip()
    
    # Parse the date and time with dateutil
    datetime_obj = parser.parse(date_time_part)
    
    # Ensure datetime is timezone-aware
    if datetime_obj.tzinfo is None:
        # Set default timezone if none is provided
        datetime_obj = datetime_obj.replace(tzinfo=datetime.timezone.utc)
    
    # Convert to UTC
    utc_datetime_obj = datetime_obj.astimezone(datetime.timezone.utc)
    
    # Format the output
    date = utc_datetime_obj.date().isoformat()
    utc_datetime = utc_datetime_obj.strftime("%Y-%m-%d %H:%M:%S")
    
    return date, utc_datetime


def is_category_irrelevant(category: str) -> bool:
    return category.strip().casefold() in categories_to_skip_casefold


def is_page_blocked(bsObj: BeautifulSoup) -> bool:
    script_tag = bsObj.find('script', src="https://ct.captcha-delivery.com/c.js")
    return bool(script_tag)


async def open_and_parse_page(browser, url):
    tab = await browser.get(url)
    time.sleep(6)
    pg_source = await tab.get_content()
    soup = BeautifulSoup(pg_source, 'html.parser')

    if is_page_blocked(soup):
        print(f"Page is blocked: {url}")
        raise RuntimeError

    return soup


def create_main_url(offset: int, section: str, date_range='past_year'):
    # offset:       Offset the results shown by the given number of articles (i.e. pagination)
    # sort:         Sort articles from newest to oldest
    # date:         Date range to search in; searching for articles in the past year
    # section:      Category of Reuters news articles to search in

    # Search for articles in the given sections that were published in the given date range, sorted from newest to oldest
    main_url = f'https://www.reuters.com/site-search/?query=*&offset={offset}&sort=newest&date={date_range}&section={section}'
    return main_url


# Returns a list of dictionaries each containing one article URL, title and UTC datetime
def parse_article_list(soup: bs4.BeautifulSoup):
    result = []

    # Each <li> tag contains one article
    article_list_soup = soup.find_all('li', class_='search-results__item__2oqiX')

    for article in article_list_soup:
        # <a> tag containing article URL and title
        article_a_tag = article.find('a', attrs={'data-testid': 'Title'})

        # <time> tag containing datetime
        article_time_tag = article.find('time', datetime=True)

        if article_a_tag and article_time_tag:
            # Extract URL
            url = BASE_URL + article_a_tag['href'].strip()

            # Extract title
            title = article_a_tag.text.strip()

            # Extract UTC date
            utc_datetime_text = article_time_tag['datetime']
            utc_date_text = utc_datetime_text.split('T')[0]

            format_string = '%Y-%m-%d'
            utc_date = datetime.datetime.strptime(utc_date_text, format_string).date()

            result.append({'url': url, 'title': title, 'utc_date': utc_date})

    return result


def extract_full_title(soup: bs4.BeautifulSoup):
    title_h1_tag = soup.find('h1')
    if title_h1_tag:
        return title_h1_tag.text.strip()

    # No title
    return None


def extract_category(soup: bs4.BeautifulSoup):
    # <nav> tag that contains the category
    category_nav_tag = soup.find('nav', attrs={'aria-label': 'Tags'})
    if category_nav_tag:

        # <a> tags each containing one category
        category_a_tags = category_nav_tag.find_all('a', attrs={'data-testid': 'Link'})

        # Use a set to remove duplicate categories
        categories = set(c.text.strip() for c in category_a_tags)
        return ', '.join(categories)

    # No category
    return None


def extract_author(soup: bs4.BeautifulSoup):
    # <div> tag that contains the authors' names
    author_div_tag = soup.find('div', class_='info-content__author-date__1Epi_')
    if author_div_tag:

        # Case 1: <a> tags each containing one author's name
        author_a_tags = author_div_tag.find_all('a')
        if author_a_tags:
            names = [name.text.strip() for name in author_a_tags]
            return ", ".join(names)


        # Case 2: <span> tag with generic author Reuters
        author_span_tag = author_div_tag.find('span', class_='text__text__1FZLe text__dark-grey__3Ml43 text__medium__1kbOh text__tag_label__6ajML')
        if author_span_tag:
            return author_span_tag.text.strip()

    # No author
    return None


def extract_date_text(soup: bs4.BeautifulSoup):
    # <time> tag containing multiple <span> elements with date text
    date_text_time_tag = soup.find('time', attrs={'data-testid':'Body'})
    if date_text_time_tag:
        return ' '.join(date_text_time_tag.stripped_strings)

    # No date text
    return None


def extract_content(soup: bs4.BeautifulSoup):
    # <div> tag that contains all the paragraphs, where each paragraph is stored in a <div> tag
    content_div_tag = soup.find('div', class_='article-body__content__17Yit')
    if content_div_tag:

        # <div> tags with 'paragraph-xx' as an attribute value
        regex = re.compile(r'paragraph-[0-9]+')
        content_paragraphs = content_div_tag.find_all('div', attrs={'data-testid': regex})

        paragraphs_text = [para.text.strip() for para in content_paragraphs]
        return '\n'.join(paragraphs_text)

    # No content
    return None


async def scrape_article(browser, url):
    failed_result = None

    soup = await open_and_parse_page(browser, url)

    try:
        full_title = extract_full_title(soup)
        category = extract_category(soup)
        author = extract_author(soup)
        date_text = extract_date_text(soup)
        content = extract_content(soup)
    except Exception as e:
        print(f"Error extracting info: {full_title}\n{url}")
        print(e)
        return failed_result
    print(date_text)

    try:
        date, utc_datetime = format_date_text(date_text)
    except Exception as e:
        print(f"Datetime conversion failed: {full_title}\n{url}")
        print(e)
        return failed_result


    # Check if this category is irrelevant
    if is_category_irrelevant(category):
        raise IrrelevantCategoryError(category)


    newArticle = Article(url, full_title, category, author, date, utc_datetime, content)

    if not newArticle.are_all_fields_present():
        return failed_result


    print("Scraping successful:", full_title)
    print(f"""Title: {full_title}
    Category: {category}
    Author: {author}
    Date: {date}
    UTC Datetime: {utc_datetime}\n""")
    return newArticle


async def scrape_and_insert_article(browser, url, title='', utc_date='', offset=0, article_num=0, num_of_articles=0):
    stats = {'article_to_insert': 0, 'article_inserted_successfully': 0, 'article_failed_insert': 0}

    try:
        print(f"Scraping: {utc_date}  Offset: {offset}  No. {article_num + 1} out of {num_of_articles}\n{title}")
        stats['article_to_insert'] = 1
        result = await scrape_article(browser, url)

        if not result or not result.are_all_fields_present():
            print(f'Scraping failed, extracted None value: {title}\n{url}\n')
            logger.error(f'Scraping failed, extracted None value  Offset: {offset}  No. {article_num + 1}\n'
                         f'{title}\n{url}\n')
            stats['article_failed_insert'] = 1
            return stats


    except IrrelevantCategoryError as e:
        print(f"Category: {e.category} not relevant, skipping: {article_num + 1} {title}\n")
        stats['article_to_insert'] = 0
        return stats

    except RuntimeError as e:
        print(f"Scraping failed, scraper has been blocked  Offset: {offset}\n{title}\n{url}\n")
        logger.critical(f"Scraping failed, scraper has been blocked  Offset: {offset}  No. {article_num + 1}\n"
                        f"{title}\n{url}\n")
        return None

    except InvalidSessionIdException as e:
        print(f"Scraping failed, scraper has invalid session ID  Offset: {offset}\n{title}\n{url}\n")
        logger.critical(f"Scraping failed, scraper has invalid session ID  Offset: {offset}  No. {article_num + 1}\n"
                        f"{title}\n{url}\n")
        return None

    except Exception as e:
        print(f'Scraping failed, unexpected error  Offset: {offset}\n{title}\n{url}\n')
        logger.error(f'Scraping failed, unexpected error  Offset: {offset}  No. {article_num + 1}\n'
                     f'{title}\n{url}\n')
        print(e)
        stats['article_failed_insert'] = 1
        return stats


    insert_result = import_into_db(collection, result)
    if insert_result:
        stats['article_inserted_successfully'] = 1

    return stats


# Scrape articles from today to end_date, where end_date is some date in the past
async def do_scraping(browser, section: str, end_date: datetime.date, offset: int=0, main_url_date_range: str=None,):
    isContinue = True

    # The largest offset Reuters website allows is 9980, any larger and the page doesn't load
    max_offset = 9980
    page_size = 20

    # Summary stats
    total_num_articles = 0
    num_articles_to_insert = 0
    num_articles_inserted_successfully = 0
    num_articles_failed_insert = 0


    # 3 exit conditions:
    # 1. Reached max offset (tested)
    # 2. No more articles to scrape (tested)
    # 3. Reached end date (tested)

    while isContinue:
        # Exit condition 1: Exceeded max offset
        if offset > max_offset:
            print(f'\nOffset {offset} exceeded max offset {max_offset}, no more articles to scrape\n')
            logger.critical(f'Offset {offset} exceeded max offset {max_offset}, no more articles to scrape\n')
            break

        main_url = create_main_url(offset, section, main_url_date_range)
        print(f'main_url: {main_url}')
        try:
            soup = await open_and_parse_page(browser, main_url)
        except RuntimeError as e:
            print(f"Scraping failed, scraper has been blocked on article list page  Offset: {offset}\n")
            logger.critical(f"Scraping failed, scraper has been blocked on article list page  Offset: {offset}\n")
            break

        except InvalidSessionIdException as e:
            print(f"Scraping failed, scraper has invalid session ID on article list page  Offset: {offset}\n")
            logger.critical(f"Scraping failed, scraper has invalid session ID on article list page  Offset: {offset}\n")
            break


        # Get a list of dictionaries containing details of each article
        article_list = parse_article_list(soup)
        num_of_articles = len(article_list)


        # Exit condition 2: No more articles to scrape
        # The page after the last page with articles contains 0 articles
        if num_of_articles == 0:
            print(f'\nEnd of article list\t  offset: {offset}\n')
            logger.critical(f'End of article list\t  offset: {offset}\n')
            break


        for article_num, article_details in enumerate(article_list):
            url = article_details['url']
            title = article_details['title']
            utc_date = article_details['utc_date']

            if not (url and title and utc_date):
                msg = f"Error extracting article info from offset {offset}: Article No. {article_num + 1} out of {num_of_articles}\n"
                print(msg)
                logger.error(msg)
                continue

            total_num_articles += 1

            # Check if article already exists
            # May not be 100% accurate since the article list title may be slightly different
            # from the full title stored in the database
            if title in existing_titles:
                print(f'Article already exists, skipping: {article_num + 1} {title}\n')
                continue


            # Exit condition 3: Reached end date
            if utc_date < end_date:
                print(f'\nFinished scraping all articles published up to {end_date}\nOffset: {offset}\n')
                logger.critical(f'Finished scraping all articles published up to {end_date}\nOffset: {offset}\n')
                # Exit outer while loop
                isContinue = False
                break


            stats = await scrape_and_insert_article(browser, url, title, utc_date, offset, article_num, num_of_articles)
            if not stats:
                # If scraper has been blocked
                # Exit outer while loop
                isContinue = False
                break

            num_articles_to_insert += stats['article_to_insert']
            num_articles_inserted_successfully += stats['article_inserted_successfully']
            num_articles_failed_insert += stats['article_failed_insert']


        # End of article_list for loop
        offset += page_size


    # End of while loop
    summaryStats = (f"Total: {total_num_articles}\n"
                    f"Articles to insert: {num_articles_to_insert}\n"
                    f"Articles inserted successfully: {num_articles_inserted_successfully}\n"
                    f"Articles failed insert: {num_articles_failed_insert}\n")

    print(summaryStats)
    logger.critical(summaryStats)


# Returns the collection after connecting to the database
def connect_to_db_collection():
    collection_name = 'Thomson_Reuters'
    # collection_name = 'Thomson_Reuters_test'

    db = common_methods.connect_db()
    collection = db[collection_name]
    print("Connected to database")
    print("Using collection:", collection_name)
    return collection


def import_into_db(collection, article: Article) -> bool:
    record = dict()

    # Create the ID based on the title and date so that database can detect duplicate articles
    _id = uuid.uuid3(uuid.NAMESPACE_DNS, article.title + article.date)
    record["_id"]           = Binary.from_uuid(_id, uuid_representation=UuidRepresentation.STANDARD)
    record["Date"]          = article.date
    record["UTC_datetime"]  = article.utc_datetime
    record["Title"]         = article.title
    record["Author"]        = article.author
    record["Content"]       = article.content
    record["Category"]      = article.category

    record["Link"]          = article.url
    record['Processed']     = 0
    record["Storage_date"]  = CurrentDate


    try:
        collection.insert_one(record)
        print(f"Inserted article: {article.title}\n{article.url}\n")
        return True

    except DuplicateKeyError as e:
        print(f'Duplicate article: {article.title}\n{article.url}\n')
        return False

    except Exception as e:
        print(f'Unexpected error inserting article: {article.title}\n{article.url}\n')
        print(e)
        return False


def set_up_logger(logs_folder: str):
    # Create the logs folder if it doesn't exist
    if not os.path.isdir(logs_folder):
        os.mkdir(logs_folder)
        print(f"Logs folder doesn't exist, creating folder: {logs_folder}")

    logger = logging.getLogger(__name__)
    return logger




categories_to_skip = ['Sports', 'Baseball', 'Soccer', 'Tennis', 'Cricket', 'Podcasts']
categories_to_skip_casefold = set(s.strip().casefold() for s in categories_to_skip)

async def main():
    # sections = {'all': 'all', 'world': 'world', 'business': 'business', 'lifestyle': 'lifestyle'}
    # sections = {'business': 'business', 'lifestyle': 'lifestyle'}
    # isTesting = True
    isTesting = False

    if isTesting:
        # Testing script


        # main_url = 'https://www.reuters.com/site-search/?query=*&offset=0&sort=newest&date=any_time&section=all'
        articleUrls = ['https://www.reuters.com/world/asia-pacific/north-koreas-kim-sacks-irresponsible-officials-over-new-town-project-2024-07-13/']


        collection = connect_to_db_collection()
        browser = await uc.start(sandbox=False)

        # result = scrape_article(articleUrl)

        for a in articleUrls:
            await scrape_and_insert_article(a)

        browser.stop()


    else:
        # Production script
        # 4. Start Chrome browser
        browser = await uc.start(sandbox=False)
        # browser.open(BASE_URL)
        browser = await login(browser)
        print("Starting to scrape\n")
        await do_scraping(browser, search_section, end_date, start_offset, date_range)

        browser.stop()

        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.critical(f"End Time: {current_time}")
if __name__ == "__main__":
    logs_folder = "logs"
    logger = set_up_logger(logs_folder)
    sections = {'business': 'business'}
    search_section = sections['business']
    end_date = datetime.date(year=2023, month=11, day=30)
    # end_date = datetime.date(year=2024, month=7, day=20)
    start_offset = 0
    date_range = 'past_week' # past_month past_week past_24_hours any_time past_year
    print(f'Searching section: {search_section}')


    # 1. Connect to MongoDB
    collection = connect_to_db_collection()

    # 2. Set up logger
    current_time_obj = datetime.datetime.now()
    current_time = current_time_obj.strftime('%Y-%m-%d %H:%M:%S')
    current_time_filename = current_time_obj.strftime('%Y-%m-%d-%H-%M-%S')

    


    # 3. Get all articles from the end_date onwards
    # Search results is a Cursor instance containing dictionaries
    db_search_results = collection.find(filter={'Date': {"$gte": str(end_date)}}, projection={'_id': False, 'Title': True})
    existing_titles = set(i['Title'] for i in db_search_results)
    print(f"Got existing titles from {end_date} onwards")
    logging.basicConfig(filename=f'./{logs_folder}/{search_section}-{current_time_filename}.log', filemode='w', encoding='utf-8',
                        format="%(levelname)s: %(message)s", force=True)
    logger.critical(f"Start Time: {current_time}")
    uc.loop().run_until_complete(main())
    

