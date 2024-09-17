import sys
sys.path.append(r'../../')
print(sys.path)
import re
import time
import uuid
import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException
import common_methods
import nodriver as uc
import logging
import pymongo
from pymongo.errors import DuplicateKeyError
import os

CurrentDate = time.strftime('%Y-%m-%d', time.localtime(time.time()))


async def login_in(browser, url):
    fail_count = 0
    login_name = 'Xuan Yao'
    username = 'nlpaidf@gmail.com'
    password = 'AIDF.NLP.2020'

    while fail_count < 5:
        try:
            tab = await browser.get(url)
            await tab.maximize()
            print('Opened home page')

            # Click the Sign In 'button' on home page
            # It's actually an <a> element styled to look like a button, not a <button> element
            elem = await tab.select('#root > div > div > div > div:nth-child(1) > header > div:nth-child(1) > div > div.style--customer-nav--2VtWGQXP > div > a.style--login--Hf7kMsAS.style--button--WR9PfOiS', timeout=15)
            await elem.click()
            print('Clicked to login page')
            time.sleep(2)

            elem = await tab.select('#emailOrUsername')
            await elem.send_keys(username)
            # Submit username
            elem = await tab.select('#signin-continue-btn')
            await elem.click()
            print("Sent username")
            time.sleep(2)

            # Fill in password in text box
            elem = await tab.select("#password")
            await elem.send_keys(password)

            # Click submit
            elem = await tab.select("#signin-pass-submit-btn")
            await elem.click()
            print("Logging in")
            time.sleep(10)

            # Check if logged in successfully
            pg_source = await tab.get_content()
            bsObj = BeautifulSoup(pg_source, 'html.parser')

            login_name_a_tag = bsObj.find('a', id="customer-nav-full-name")
            if login_name_a_tag and login_name_a_tag.text.strip() == login_name:
                print("Login successful")
                return browser
            else:
                print("Login failed, possibly blocked")
                return None

        except Exception as e:
            print(e)
            fail_count += 1

    # Unable to login
    return None


def is_page_blocked(bsObj: BeautifulSoup) -> bool:
    script_tag = bsObj.find('script', src="https://ct.captcha-delivery.com/c.js")
    return bool(script_tag)


def can_skip_topic(topic: str) -> bool:
    return topic.strip().casefold() in topics_to_skip_casefold


def import_into_db(date, utc_date_time, title, author, content, category, link, collection):
    record = dict()

    # Create the ID based on the title and date so that database can detect duplicate articles
    _id = str(uuid.uuid3(uuid.NAMESPACE_DNS, title + date))
    record["_id"] = _id

    record["Date"] = date
    record["UTC_datetime"] = utc_date_time
    record["Title"] = title
    record["Author"] = author
    record["Content"] = content
    record["Category"] = category
    record["Link"] = link
    record['Processed'] = 0
    record["Storage_date"] = CurrentDate

    try:
        collection.insert_one(record)
        print(f"Inserted article: {title}\n{link}\n")
        return True

    except DuplicateKeyError as e:
        print(f'Duplicate article: {title}\n{link}\n')
        return False

    except Exception as e:
        print(f'Unexpected error inserting article: {title}\n{link}\n')
        print(e)
        return False


# Returns the date, time and timezone
def format_date(date_input):
    if "." in date_input:
        month = re.search(re.compile(r"[a-zA-Z]+(?=. \d)"), date_input)[0][0:3]
        day = re.search(re.compile(r"[0-9]+(?=,)"), date_input)[0]
        year = re.search(re.compile(r"(?<=, )[0-9]+"), date_input)[0]

        hr = re.search(re.compile(r"[0-9]+(?=:)"), date_input)[0]
        min = re.search(re.compile(r"(?<=:)[0-9]+"), date_input)[0]
        Am_Pm = re.search(re.compile(r"(?<=:[0-9][0-9] )[a-zA-Z]+"), date_input)[0]
        time = datetime.datetime.strptime(" ".join([":".join([hr, min]), Am_Pm]), "%I:%M %p").time()

        time_zone = re.search(re.compile(r"(?<=:[0-9][0-9] [a-zA-Z][a-zA-Z] )[a-zA-Z]+"), date_input)[0]

        return str(datetime.datetime.strptime(year + month + day, "%Y%b%d").date()), str(time), str(time_zone)

    else:
        month = re.search(re.compile(r"[a-zA-Z]+(?= \d+,)"), date_input)[0]
        day = re.search(re.compile(r"[0-9]+(?=,)"), date_input)[0]
        year = re.search(re.compile(r"(?<=, )[0-9]+"), date_input)[0]

        try:
            hr = re.search(re.compile(r"[0-9]+(?=:)"), date_input)[0]
            min = re.search(re.compile(r"(?<=:)[0-9]+"), date_input)[0]
            Am_Pm = re.search(re.compile(r"(?<=:[0-9][0-9] )[a-zA-Z]+"), date_input)[0]

            time_zone = re.search(re.compile(r"(?<=:[0-9][0-9] [a-zA-Z][a-zA-Z] )[a-zA-Z]+"), date_input)[0]

        # Use 12:01 AM ET if unable to extract time and timezone
        except Exception as e:
            hr = '12'
            min = '01'
            Am_Pm = 'am'
            time_zone = 'ET'


        time = datetime.datetime.strptime(" ".join([":".join([hr, min]), Am_Pm]), "%I:%M %p").time()

        try:
            return str(datetime.datetime.strptime(year+month+day, "%Y%B%d").date()), str(time), str(time_zone)
        except:
            return str(datetime.datetime.strptime(year+month+day, "%Y%b%d").date()), str(time), str(time_zone)


# Formats author information from a list of tokens
def format_author_from_tokens(tokens: list):
    # Case 1: 1 token -> 1 author, 4th character onwards
    # E.g. "By John Doe"
    if len(tokens) == 1:
        return tokens[0][3:].strip()

    # Case 2: 2 or 3 tokens -> 1 author, 2nd token
    # E.g. "By" "John Doe" "/ Photographs by Jane Doe"
    if len(tokens) == 2 or len(tokens) == 3:
        return tokens[1].strip()

    # Case 3: 4 tokens -> 2 authors, 2nd and 4th tokens
    # E.g. "By" "John Doe" "and" "Jane Doe"
    elif len(tokens) == 4:
        return f"{tokens[1].strip()}, {tokens[3].strip()}"

    # Case 4: 6 tokens -> 3 authors, 2nd, 4th and 6th tokens
    # E.g. "By" "John Doe" "," "Jane Doe" "and" "Tom Doe"
    elif len(tokens) == 6:
        return f"{tokens[1].strip()}, {tokens[3].strip()}, {tokens[5].strip()}"

    # Else unable to parse author info
    else:
        return ""


def extract_title(bsObj: BeautifulSoup) -> str:
    title = None

    title_h1_tag = bsObj.find('h1')
    if title_h1_tag:
        title = title_h1_tag.string.strip()

    return title


# Extract author(s) of the article
def extract_author(bsObj: BeautifulSoup) -> str:
    author = ""

    # Case 1: <span> tag within author-link <a> tag
    author_span_tags = bsObj.find_all('span', class_='css-1wc2zh5')
    if author_span_tags:
        names = [name.string for name in author_span_tags]
        author = ", ".join(names)

    else:
        # Case 2: AuthorContainer <span> tag that contains <a> tag
        author_span_tags = bsObj.find_all('span', class_='css-nyr2iw-AuthorContainer e1575iv83')
        if author_span_tags:
            names = [name.a.string for name in author_span_tags]
            author = ", ".join(names)

        else:
            # Case 3: <p> tags containing entire author line string in plaintext (not clickable link)
            author_p_tags = bsObj.find_all('p', class_='epvx9352 css-1s90smj-AuthorPlaintext')
            if author_p_tags:
                author_line_words = [word.string for word in author_p_tags]
                author = format_author_from_tokens(author_line_words)

            else:
                # Case 4: PlainByline <span> tag within AuthorContainer <span> tag
                author_span_tags = bsObj.find_all('span', class_='css-1qf7jf5-PlainByline e10pnb9y1')
                if author_span_tags:
                    names = [name.string for name in author_span_tags]
                    author = ", ".join(names)


    return author


def extract_date_text(bsObj: BeautifulSoup) -> str:
    date_text = None

    # Case 1: The timestamp and timezone are stored in separate children tags under this <p> tag
    # So concatenate all child strings together to form the date text
    date_text_p_tag = bsObj.find('p', attrs={"data-testid": "timestamp-text"})
    if date_text_p_tag:
        date_text = "".join(date_text_p_tag.strings)

    else:
        # Case 2: The timestamp and timezone are stored in a single string in the same tag
        date_text_time_tag = bsObj.find('time', class_='css-1u347bo-Timestamp-Timestamp emlnvus2')
        if date_text_time_tag:
            date_text = date_text_time_tag.text

    return date_text


def extract_content(bsObj: BeautifulSoup) -> str:
    para_list = bsObj.find('main').find('article')
    para_list = para_list.findAll('p')

    content = ""
    for para in para_list:
        para_text = para.text
        if '\n' in para_text:
            para_text = para_text.replace('\n', ' ')

        if 'Write to' in para_text \
                or '@wsj.com' in para_text \
                or 'contributed to this article' in para_text \
                or 'Copyright' in para_text:
            break

        content += ("\n" + para_text)

    return content


async def extract_information_soup(url, browser):
    failed_result = None, None, None, None, None
    retry_count = 0
    retry_limit = 2

    while retry_count < retry_limit:
        tab = await browser.get(url)
        await tab.maximize()

        pg_source = await tab.get_content()
        bsObj = BeautifulSoup(pg_source, 'html.parser')

        if is_page_blocked(bsObj):
            print("Page is blocked:", url)
            raise RuntimeError

        try:
            title = extract_title(bsObj)
            author = extract_author(bsObj)
            date_text = extract_date_text(bsObj)
            content = extract_content(bsObj)

        except NoSuchElementException as e:
            print(f"Error extracting info: {title}\n{url}")
            print(e)
            retry_count += 1
            time.sleep(1)
            continue


        if not title:
            print(f"Missing title: {url}")
            retry_count += 1
            continue

        if not author:
            print(f"Missing author: {title}\n{url}")

        if not date_text:
            print(f"Missing date_text: {title}\n{url}")
            retry_count += 1
            continue

        if content == '':
            print(f"Empty article: {title}\n{url}")
            retry_count += 1
            continue


        try:
            date, time_, time_zone = format_date(date_text)
            date_time = " ".join([date, time_])
            utc_dt = common_methods.convert_LocalToUtc_Date(date_time, time_zone=time_zone)

        except Exception as e:
            print(f"Datetime conversion failed: {title}\n{url}")
            print(e)
            retry_count += 1
            continue


        print("Scraping successful:", title)
        print(f"""Title: {title}
        Author: {author}
        Date: {date}
        UTC Datetime: {utc_dt}\n""")
        return date, utc_dt, title, author, content


    print(f"Exceeded retry limit, unable to scrape article: {title}\n{url}")
    return failed_result


async def do_scrapy(date, browser, existed_title, logger, collection, start_page=1, skip_articles=0):
    page_num = start_page

    # Summary stats
    total_num_articles = 0
    num_articles_to_insert = 0
    num_articles_inserted_successfully = 0
    num_articles_failed_insert = 0


    while True:
        # Need to zero-pad the month and date to retrieve the right page
        print(f'Working on {date}  page: {page_num}')
        main_url = f"https://www.wsj.com/news/archive/{date.year}/{date.month:02}/{date.day:02}?page={page_num}"


        # Get main url which is the contents page of articles
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(main_url, headers=headers)
            bsObj = BeautifulSoup(r.text, 'html.parser')
        except Exception as e:
            print(f'\nError getting article list page\t{date}  page: {page_num}\n')
            logger.error(f'Error getting article list page\t{date}  page: {page_num}\n')
            print(e)
            break


        # Extract a list of all articles
        try:
            working_area = bsObj.find('ol', {'class': 'WSJTheme--list-reset--3pR-r52l'})
            article_list = working_area.findAll('article')
            num_articles_on_page = len(article_list)

            # The page after the last page with articles contains 0 articles
            if num_articles_on_page == 0:
                print(f'\nEnd of article list\t{date}  page: {page_num}\n')
                break

        except Exception as e:
            print(f'\nError parsing article list page\t{date}  page: {page_num}\n')
            logger.error(f'Error parsing article list page\t{date}  page: {page_num}\n')
            print(e)
            break


        # Process each article on this contents page
        total_num_articles += num_articles_on_page

        # Skip past the specified number of articles
        e = enumerate(article_list)
        for i in range(skip_articles):
            e.__next__()

        for article_num, article in e:
            try:
                # Find article url
                article_a_tag = article.find('h2').find('a')
                url = article_a_tag.get('href')

                # Find title
                title = article_a_tag.text

                # Find topic
                topic = article.find('div', {'class': 'WSJTheme--articleType--34Gt-vdG'}).text
                if can_skip_topic(topic):
                    print(f"Topic: {topic} not relevant, skipping: {article_num + 1} {title}\n")
                    continue

            except Exception as e:
                print(f"Error extracting article info from page {page_num}: Article No. {article_num + 1} out of {num_articles_on_page}\n")
                logger.error(f"Error extracting article info from page {page_num}: Article No. {article_num + 1} out of {num_articles_on_page}\n")
                print(e)
                continue


            # If article already exists in database
            if title in existed_title:
                print(f'Article already exists, skipping: {article_num + 1} {title}\n')
                continue

            # Else article is not in database
            else:
                try:
                    print(f"Scraping: {date.date()}  Page: {page_num}  No. {article_num + 1} out of {num_articles_on_page}\n"
                          f"Topic: {topic}\n{title}")
                    num_articles_to_insert += 1
                    Date, UTC_Date_Time, Title, Author, Content = await extract_information_soup(url, browser)

                    if not (Date and UTC_Date_Time and Title and Content):
                        print(f'Scraping failed, extracted None value: {title}\n{url}\n')
                        logger.error(f'Scraping failed, extracted None value: {date.date()}  Page: {page_num}  No. {article_num + 1}\n'
                                     f'{title}\n{url}\n')
                        num_articles_failed_insert += 1
                        continue

                    # Warn if no author but continue to insert
                    elif not Author:
                        logger.warning(f"Missing author: {date.date()}  Page: {page_num}  No. {article_num + 1}\n"
                                       f"{title}\n{url}\n")


                except RuntimeError as e:
                    print(f"Scraping failed, scraper has been blocked\n{title}\n{url}\n")
                    logger.critical(f"Scraping failed, scraper has been blocked: {date.date()}  Page: {page_num}  No. {article_num + 1}\n"
                                    f"{title}\n{url}\n")
                    return

                except Exception as e:
                    print(f'Scraping failed, unexpected error: {title}\n{url}\n')
                    logger.error(f'Scraping failed, unexpected error: {date.date()}  Page: {page_num}  No. {article_num + 1}\n'
                                 f'{title}\n{url}\n')
                    print(e)
                    num_articles_failed_insert += 1
                    continue

                insert_result = import_into_db(Date, UTC_Date_Time, Title, Author, Content, topic, url, collection)
                existed_title.add(Title)

                if insert_result:
                    num_articles_inserted_successfully += 1

        page_num += 1

    print('Finished scraping all articles published on', date)
    summaryStats = (f"Total: {total_num_articles}\n"
          f"Articles to insert: {num_articles_to_insert}\n"
          f"Articles inserted successfully: {num_articles_inserted_successfully}\n"
          f"Articles failed insert: {num_articles_failed_insert}\n")

    print(summaryStats)
    logger.critical(summaryStats)


topics_to_skip = ['Soccer', 'Crossword', 'Letters', 'Slideshow', 'Pepper & Salt', 'Journal Reports: College Rankings',
                  'Arts Calendar', 'Future View', 'Notable & Quotable', 'Food & Drink', 'House Call', 'Music Review',
                  'Film Review', 'Art Review', 'Variety Puzzle', 'Fashion', 'Crossword Contest', 'Number Puzzles',
                  'Annotated Room', 'Bookshelf', 'My Ride', 'Homes', 'Managing Your Career', 'Sports', 'Style & Substance',
                  'What to Watch', 'The Saturday Essay', 'Essay', 'News Quiz', 'Television Review', 'Masterpiece',
                  'Table Talk', 'Television', 'Music', 'Theater Review', 'Opera Review', 'Style', 'Exhibition Review',
                  'Obituary', 'Dance Review', 'Cultural Commentary', 'Architecture Review', 'Book Review', 'Humor', 'NHL',
                  'NBA', 'NFL', 'MLB', 'About Face', 'Off Duty Travel', 'Private Properties']
topics_to_skip_casefold = set(s.casefold() for s in topics_to_skip)


async def main():
    # isTesting = True
    isTesting = False

    if isTesting:
        # Testing script
        home_page_url = 'https://www.wsj.com/'

        isHeadless = False
        # isHeadless = True
        if isHeadless:
            print("Starting browser in headless mode")

        browser = await uc.start()
        browser = await login_in(browser, home_page_url)

        if not browser:
            print("Exiting")
            exit()

        # logger = logging.getLogger(__name__)
        # logging.basicConfig(filename=f'wsjScript.log', encoding='utf-8', format="%(levelname)s: %(message)s", force=True)

        # articleUrl = 'https://www.wsj.com/economy/central-banking/bojs-nakamura-says-appropriate-to-maintain-monetary-policy-for-time-being-e95ae618'
        # articleUrl = 'https://www.wsj.com/style/raw-milk-unpasturized-health-influencers-fda-d65d9aab'
        # articleUrl = 'https://www.wsj.com/tech/the-ceo-trapped-in-the-u-s-china-chip-battle-7340c949'
        articleUrl = 'https://www.wsj.com/livecoverage/stock-market-today-dow-jones-05-07-2024?mod=article_inline'
        await extract_information_soup(articleUrl, browser)

        browser.stop()
        exit()

        col_name = "The_Wall_Street_Journal"
        # col_name = 'The_Wall_Street_Journal_test'

        db = common_methods.connect_db()
        print("Connected to database")
        collection = db[col_name]
        print("Using collection:", col_name)


        date = pd.Timestamp(year=2024, month=1, day=31)
        existed_title = set(i['Title'] for i in collection.find({'Date': str(date.date())}, projection={'_id': False, 'Title': True}))

        logger = logging.getLogger(__name__)
        logging.basicConfig(filename=f'./logs/{date.date()}.log', filemode='w', encoding='utf-8',
                            format="%(levelname)s: %(message)s", force=True)

        start_page = 1
        num_of_articles_to_skip = 0
        await do_scrapy(date, browser, start_page, num_of_articles_to_skip)

        browser.quit()
        exit()


    else:
        # Production script
        col_name = "The_Wall_Street_Journal"

        db = common_methods.connect_db()
        print("Connected to database")
        collection = db[col_name]
        print("Using collection:", col_name)


        # Get the date of the most recent article in the database
        max_date = collection.find_one(sort=[('Date', pymongo.DESCENDING)])['Date']
        print("Using max date", max_date)


        # Set the date range to (max_date, max_date + days_to_scrape]
        days_to_scrape = 5
        start_date = datetime.datetime(int(max_date[:4]), int(max_date[5:7]), int(max_date[-2:]))
        end_date = start_date + datetime.timedelta(days=5)
        date_list = pd.date_range(start_date, end_date, inclusive='right')


        # # Manually set the start and end date
        # start_date = datetime.datetime(year=2024, month=7, day=10)
        # end_date   = datetime.datetime(year=2024, month=8, day=5)
        # date_list = pd.date_range(start_date, end_date)

        print(f"Computed date list from {date_list[0].date()} to {date_list[-1].date()}")


        # Get all articles from the start_date onwards
        existed_title = set(i['Title'] for i in collection.find({'Date': {"$gte": str(start_date.date())}},
                                                                projection={'_id': False, 'Title': True}))
        print(f"Got existing titles from {start_date.date()} onwards")



        # Set up web scraper
        home_page_url = 'https://www.wsj.com/'

        isHeadless = False
        # isHeadless = True
        if isHeadless:
            print("Starting browser in headless mode")

        browser = await uc.start()
        browser = await login_in(browser, home_page_url)

        if not browser:
            print("Exiting")
            exit()

        # Set up logger
        logger = logging.getLogger(__name__)

        print("Starting to scrape")
        if not os.path.exists('./logs'):
            os.makedirs('./logs')
        for date in date_list:
            logging.basicConfig(filename=f'./logs/{date.date()}.log', filemode='w',
                                format="%(levelname)s: %(message)s", force=True)
            await do_scrapy(date, browser, existed_title, logger, collection)


        browser.stop()

if __name__ == "__main__":
    uc.loop().run_until_complete(main())

    

