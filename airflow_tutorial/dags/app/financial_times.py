# -*- coding: utf-8 -*-
from urllib.request import urlopen
from bs4 import BeautifulSoup
import re
import sys
import datetime
import sys
sys.path.append(r'../../')
import common_methods


def format_date(date_input):

    date_time = date_input.split("T")
    date = date_time[0]
    date = str(datetime.datetime.strptime(date, "%Y-%m-%d").date())

    time = date_time[1][:8]
    hr = re.search(re.compile(r"[0-9]+(?=:)"), time)[0]
    min = re.search(re.compile(r"(?<=:)[0-9]+"), time)[0]
    time = ":".join([hr, min, "00"])

    time_zone = "UTC"

    return str(date), str(time), time_zone
def get_article(url):
    try:
        r = urlopen(url)
        bsObj = BeautifulSoup(r, "html.parser")

        title = bsObj.find("h1").find('span').text

        date_text = str(bsObj.find(
            'time', {'class': 'article-info__timestamp o-date'}))
        date_text = date_text.split('"')
        date_text = date_text[-2]
        date, time_, time_zone = format_date(date_text)
        date_time = " ".join([date, time_])
        utc_dt = common_methods.convert_LocalToUtc_Date(date_time, input_time_zone=time_zone)

        #date = str(datetime.datetime.strptime(Date_text, "%Y-%m-%d").date())

        if title == 'Further reading':
            print('No content!!!\t')
            return None, None, None, None
        else:
            try:
                author = bsObj.find(
                    'p', {'class': 'article-info__byline'}).text
            except:
                author = 'ft'

            content_body = bsObj.find(
                'div', {'class': 'article__content-body n-content-body js-article__content-body'})
            if content_body == None:
                content_body = bsObj.find('article', {'class': 'n-content-body js-article__content-body'})
            paragraph = content_body.findAll("p")
            p = [j.get_text() for j in paragraph]

            try:
                ad_text = bsObj.find(
                    'div', {'class': 'n-content-layout__slot'}).text
                if ad_text in p:
                    p.remove(ad_text)
            except:
                pass
            ad_text_custom = "Your browser does not support"
            for i in p:
                if ad_text_custom in i:
                    print('Video')
                    return None, None, None, None, None
            p = [i for i in p if ad_text_custom not in i]
            content = "\n".join(p)
    except:
        print('Get article error!!!')
        return None, None, None, None, None

    return date, utc_dt, title, author, content


def get_article_links(url):
    links = []
    try:
        html = urlopen(url)
        bsObj = BeautifulSoup(html, "html.parser")
        links = bsObj.find("div", {"data-trackable": "stream"}).findAll("div", {"class": "o-teaser__heading"})
    except:
        print('Get article links fail!!!')

    return links


def do_scrapy(category):
    page = 1
    fail_count = 0
    while fail_count <= 5:
        print('Start working on category {}, page {}'.format(category, page))
        url = "https://www.ft.com/" + category + "?page=" + str(page)

        links = get_article_links(url)
        if not links:
            fail_count += 1
            print('Get category {}, page {} error, fail count {}'.format(category, page, fail_count))
        else:
            page += 1

        for m in links:
            url = "https://www.ft.com" + m.find("a").get('href')
            if url not in EXIST_ARTICLES:
                try:
                    date, utc_date_time, title, author, content = get_article(url)
                    data = {
                        'date': date,
                        'utc_date_time': utc_date_time,
                        'title': title,
                        'author': author,
                        'content': content,
                        'link': url,
                        'category': category
                    }
                    if content:
                        import_sucess = common_methods.import_into_db(data, collection)
                        if import_sucess:
                            EXIST_ARTICLES.add(url)
                except:
                    print('Fail!!!\t', url)
            else:
                print('Article existed!!!\t', url)

    print('Finished!!!\t', category)


if __name__ == "__main__":
    category_list = ["global-economy", "world/uk", "world/us", "world/asia-pacific/china", "world/africa",
                     "world/asia-pacific", "emerging-markets", "world/europe", "world/americas", "world/mideast",
                     "us-economy", "us-economy", "companies/us", "world/us/politics","companies/health", "companies/industrials",
                     "companies/media", "companies/energy", "companies/professional-services", "companies/retail-consumer",
                     "companies/financials", "companies/technology", "companies/telecoms", "companies/transport",
                     "companies/insurance", "companies/property", "companies/financial-services", "accounting-consulting-services",
                     "companies/legal-services", "companies/recruitment-services",
                     "banks", "technology", "alphaville", "oil", "gold", "copper", "equities",
                     "us-equities", "uk-equities", "european-equities", "asia-pacific-equities", "ftfm", "fund-regulation",
                     "pensions-industry", "ft-trading-room", "ft-trading-room/clearing-settlement", "ft-trading-room/high-frequency-trading", "markets",
                     "capital-markets", "commodities", "currencies", "equities", "fund-management", "trading",
                     "moral-money", "financial-markets-regulation", "otc-markets", "derivatives", "opinion", "moral-money",
                     "climate-capital", "ft-view", "the-big-read", "lex", "letters"]

    DB = common_methods.connect_db()
    col_name = 'Financial_Times'
    collection = DB[col_name]

    EXIST_ARTICLES = set()
    for i in collection.find():
        EXIST_ARTICLES.add(i["Link"])

    # Parallel(n_jobs=len(category_list))(delayed(do_scrapy)(category) for category in category_list)
    for category in category_list:
        do_scrapy(category)
    #do_scrapy("global-economy")
