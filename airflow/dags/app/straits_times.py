import re
#import ray
import time
import uuid
import datetime
from urllib.request import urlopen
from bs4 import BeautifulSoup
from bson import Binary, UuidRepresentation
import nodriver as uc
from selenium.common.exceptions import NoSuchElementException

import sys
sys.path.append(r'../../')
import common_methods
def import_into_db(date, utc_date_time, title, author, content, category, link, collection):
    record = dict()
    try:
        _id = uuid.uuid3(uuid.NAMESPACE_DNS, title + date)
        record["_id"] = Binary.from_uuid(_id, uuid_representation=UuidRepresentation.STANDARD)
        record["Date"] = date
        record["UTC_datetime"] = utc_date_time
        record["Title"] = title
        record["Author"] = author
        record["Content"] = content
        record["Category"] = category
        record["Link"] = link
        record['Processed'] = 0
        record["Storage_date"] = CurrentDate
        print('insert', title)
        collection.insert_one(record)
        print("Insertion successful!")
    except Exception as e:
        print(f'Error in inserting article: {e}')
        pass

# def login_in():
#     browser = common_methods.get_driver()

#     # Login in
#     source_url = 'https://www.straitstimes.com'
#     # browser.maximize_window()
#     browser.get(source_url)
#     browser.implicitly_wait(5)
#     browser.refresh()

#     username = 'nlpaidf@gmail.com'
#     password = 'AIDF.CRI.NLP.2020'

#     browser.switch_to.default_content()
#     """browser.find_element(by=By.ID, value='pclose-btn').click()
#     time.sleep(2)"""
#     # browser.find_element(by=By.CSS_SELECTOR, value='a#sph_login.mysph_login').click()
#     # browser.find_element(by=By.CSS_SELECTOR, value='#sph_login').click()
#     time.sleep(5)
#     browser.implicitly_wait(2)
#     button = browser.find_element(by=By.CSS_SELECTOR, value='#sph_login')
#     time.sleep(5)
#     browser.implicitly_wait(2)
#     browser.execute_script("arguments[0].click();", button)
#     browser.find_element(by=By.NAME, value='IDToken1').send_keys(username)
#     browser.find_element(by=By.NAME, value='IDToken2').send_keys(password)
#     button = browser.find_element(by=By.ID, value='btnLogin')
#     browser.execute_script("arguments[0].click();", button)
#     time.sleep(5)
#     browser.implicitly_wait(2)
#     try:
#         browser.find_element(by=By.ID, value='btnMysphMsg').click()
#     except:
#         pass

#     browser.implicitly_wait(10)

#     # print(c)
#     # pickle.dump(browser.get_cookies(), open("cookies.pkl", "wb"))

#     return browser

def format_date(date_input):

    month = re.search(re.compile(r"[a-zA-Z]+(?= \d+,)"), date_input)[0]
    day = re.search(re.compile(r"[0-9]+(?=,)"), date_input)[0]
    year = re.search(re.compile(r"(?<=, )[0-9]+"), date_input)[0]
    date = str(datetime.datetime.strptime(year+month+day, "%Y%b%d").date())

    hr = re.search(re.compile(r"[0-9]+(?=:)"), date_input)[0]
    min = re.search(re.compile(r"(?<=:)[0-9]+"), date_input)[0]
    Am_Pm = re.search(re.compile(r"(?<=:[0-9][0-9] )[a-zA-Z]+"), date_input)[0]
    time_out = str(datetime.datetime.strptime(" ".join([":".join([hr, min]), Am_Pm]), "%I:%M %p").time())

    time_zone = "Asia/Singapore"

    return date, time_out, time_zone

async def extract_information_soup(url, browser):
    retry_flag = True
    retry_count = 0
    while retry_flag:
        if retry_count < 2:
            try:
                tab = await browser.get(url)
                time.sleep(2)
                # headers = {'User-Agent': 'Mozilla/5.0'}
                #r = requests.get(url, headers=headers, cookies=cookies)
                # cookies = pickle.load(open("cookies.pkl", "rb"))
                # for cookie in cookies:
                #     browser.add_cookie(cookie)
                page_source = await tab.get_content()
                bsObj = BeautifulSoup(page_source, 'html.parser')

                Title = bsObj.find('h1', {'class': 'headline node-title'}).text.strip()
                Author = ''
                try:
                    Author = bsObj.find('div', {'class': 'author-field author-name'}).text
                    print(Author)
                except:
                    try:
                        Author = bsObj.find('div', {'class': 'group-info'}).text.strip()
                    except:
                        pass

                date_text = bsObj.find('div', {'class': 'story-postdate'}).text.strip()
                Date, Time, Time_zone = format_date(date_text)
                Date_time = ' '.join([Date, Time])
                UTC_dt = common_methods.convert_LocalToUtc_Date(Date_time, input_time_zone=Time_zone)

                para_list = bsObj.find('div', {'class': 'ds-wrapper article-content-rawhtml'})
                para_list = para_list.findAll('p')
                if 'Please subscribe or log in' in para_list[-2] or '*Terms and conditions apply.' in para_list[-1]:
                    print('Cookie outdated!!!')
                    return
                Content = "\n".join(map(lambda para: para.text, para_list))

                retry_flag = False
            except NoSuchElementException:
                retry_count += 1
                time.sleep(1)
                continue
        else:
            break

    return Date, UTC_dt, Title, Author, Content

# Loop topic list
# @ray.remote
async def do_scrapy(browser, topic):
    # Initialize database
    db = common_methods.connect_db()
    collection = db.The_Strait_Times

    source_url = 'https://www.straitstimes.com'
    # Urls already exist
    #existed_title = set([i['Title'] for i in collection.find()])
    EXIST_ARTICLES = set()
    for i in collection.find():
        try:
            EXIST_ARTICLES.add(i['link'])
        except:
            try:
                EXIST_ARTICLES.add(i['Link'])
            except:
                pass

    flag = True
    page = 0

    fail_count = 0
    while flag and fail_count < 5:
        print('Working on ', topic, '  page: ', page)
        main_url = source_url + '/' + topic + '?page=' + str(page)
        page += 1
        try:
            html = urlopen(main_url)
            bsObj = BeautifulSoup(html, "html.parser")
        except:
            fail_count += 1
            print('\nPage url error ', topic, '  page: ', page, '\n')
            page -= 1
            continue

        try:
            working_area = bsObj.find('div', {'class': 'view-content'}).find('div', {'class': 'view-content'})
            article_list = working_area.findAll('h5')
        except:
            fail_count += 1
            continue

        duplicated_count = 0
        for article in article_list:

            url = source_url + article.a['href']
            title = article.text.strip()

            if url in EXIST_ARTICLES:
                duplicated_count += 1
                if duplicated_count >= 5:
                    #flag = False
                    break
                print('Exist!!!\t', title)
                continue
            else:
                try:
                    Date, UTC_dt, Title, Author, Content = await extract_information_soup(url, browser)
                except:
                    print('Fail!!!\t', url)
                    continue
                #print([Date, UTC_dt, Title, Author, Content])
                import_into_db(Date, UTC_dt, Title, Author, Content, topic, url, collection)
                EXIST_ARTICLES.add(Title)
    print('Finished!!!\t', topic)
    
async def main():
    # browser = login_in()
    browser = await uc.start(sandbox=False)

    
    for topic in topic_list:
        await do_scrapy(browser, topic)

if __name__ == "__main__":
    CurrentDate = time.strftime('%Y-%m-%d',time.localtime(time.time()))

    # Topic list
    topic_list = ['singapore/jobs', 'singapore/housing', 'singapore/politics',
                'singapore/health', 'singapore/transport', 'singapore/courts-crime',
                'singapore/consumer', 'singapore/environment', 'singapore/community',
                'asia/se-asia', 'asia/east-asia', 'asia/south-asia', 'asia/australianz',
                'world/united-states', 'world/europe', 'world/middle-east', 'opinion',
                'opinion/st-editorial', 'business/invest', 'business/banking', 'business/companies-markets',
                'business/property', 'tech/tech-news']

    # with open('cookie.txt', 'r', encoding='utf-8') as f:
    #     cookie = f.read()
    # cookies = json.loads(cookie)
    
    uc.loop().run_until_complete(main())
    '''ray.init()

    ray.get([do_scrapy.remote(topic) for topic in topic_list])'''


"""with parallel_backend('threading', n_jobs=len(topic_list)):
    Parallel()(delayed(do_scrapy)(topic) for topic in topic_list)
"""