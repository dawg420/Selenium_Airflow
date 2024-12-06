from bs4 import BeautifulSoup
import datetime
# import ray
import sys
import re
sys.path.append(r'../')
import common_methods
import warnings
warnings.filterwarnings('ignore')
import nodriver as uc
from datetime import datetime

def convert_24hrs(t):
    var = datetime.strptime(t, "%I:%M:%S %p")
    v_res = datetime.strftime(var, '%H:%M:%S')
    return v_res

async def get_article_links(p):
    await p.wait(2)
    html = await p.get_content()
    # print(await p.get_all_urls())
    bs = BeautifulSoup(html, 'html.parser')
    # print(bs.prettify())
    res_list_0 = bs.select('h6[class="hit-name h6 list-object__heading"]')
    # print(f'res_list: {res_list_0}')
    a_list = []
    href_list = []

    for res in res_list_0:
        link_list_1 = res.select('a')
        for link in link_list_1:  # a
            href = link.get('href')
            a_list.append(href)

    for i in a_list:
        if '/watch/' not in i:
            href_list.append(i)

    return href_list

async def extract_information(browser, link):
    p = await browser.get(link)
    await p.maximize()
    html = await p.get_content()
    bsobj = BeautifulSoup(html, 'html.parser')

    # Get the Title
    title_res = bsobj.select('h1[class="h1 h1--page-title"]')
    title = title_res[0].get_text().strip() if title_res else ""

    # Author
    try:
        author_res = bsobj.select('div[class="mobile_author_card__name"]')
        author = author_res[0].get_text().strip() if author_res else ""
        author = re.sub(r'\s(?=\s)', '', re.sub(r'\s', ' ', author))
    except:
        author = 'CNA'

    # Text
    text_res = bsobj.select('div[class="text-long"]')
    text = "\n".join([item.get_text().strip() for item in text_res if item.get_text()]).strip()

    # Remove irrelevant parts
    for unwanted in ["Best News Website or Mobile Service", "WAN-IFRA Digital Media Awards Worldwide", "Advertisement", "Digital Media Awards Worldwide 2022"]:
        text = text.replace(unwanted, "")
    content = text.strip()

    # Extract date and time
    try:
        date_text = await p.select('#block-mc-cna-theme-mainpagecontent > article:nth-child(1) > div.content > div:nth-child(3) > div.layout__region.layout__region--second > section.block.block-mc-content-share-bookmark.block-content-share-bookmark.clearfix > div.article-publish.article-publish--')
        date_text = date_text.text.strip()
    except:
        try:
            date_text = await p.select("#block-mc-cna-theme-mainpagecontent > article > div.content > div:nth-child(3) > div.layout__region.layout__region--second > section > div.article-publish.article-publish--.block.block-mc-content-share-bookmark.block-content-share-bookmark.clearfix")  
            date_text = date_text.text.strip()
        except:
            try:
                date_text = await p.select('#block-mc-cnaluxury-theme-mainpagecontent > article:nth-child(1) > div.content > div:nth-child(3) > div.layout__region.layout__region--second > section.block.block-mc-content-share-bookmark.block-content-share-bookmark.clearfix > div.article-publish.article-publish--')
                date_text = date_text.text.strip()
            except: 
                try:
                    date_text = await p.select('#block-mc-cnalifestyle-theme-mainpagecontent > article > div.content > div:nth-child(3) > div.layout__region.layout__region--second > section > div.article-publish.article-publish--.block.block-mc-content-share-bookmark.block-content-share-bookmark.clearfix')
                    date_text = date_text.text.strip()
                except:
                    date_text = ""
    date_text = ' '.join(date_text.split(' ')[1:4]) if 'Updated' in date_text else ' '.join(date_text.split(' ')[:-1])
    print(f'date_text: {date_text}')
    
    if date_text != "":
        date_res_1 = datetime.strptime(date_text, "%d %b %Y")
        new_date = date_res_1.strftime('%Y-%m-%d')
    else:
        new_date = ""
        utc_date_time = ""


    time_res = bsobj.select(
        'div[class="article-publish article-publish-- block block-mc-content-share-bookmark block-content-share-bookmark clearfix"]')
    if len(time_res) == 0:
        time_res_line = "12:00 AM"
    else:
        time_res_line = time_res[0].get_text()
    first_match = re.search(pattern="[0-9]+[0-9]:[0-9]+[0-9]+", string=time_res_line)
    if first_match is None:
        first_match_try = re.search(pattern="[0-9]:[0-9]+[0-9]+", string=time_res_line)
        o = first_match_try.group()
    else:
        o = first_match.group()

    i = o + ':00'
    second_match = re.search(pattern="(AM|PM)", string=time_res_line)
    if second_match:
        c = second_match.group()
    else:
        c = "AM"
    k = (" ".join([i, c]))
    hrs_24 = convert_24hrs(k)

    if new_date != "":
        prepared_utc = (" ".join([new_date, hrs_24]))

        utc_date_time = common_methods.convert_LocalToUtc_Date(prepared_utc, input_time_zone="Asia/Singapore")

    return title, author, content, new_date, utc_date_time

async def do_scrapy(browser, category, category_id):
    # connect database
    db = common_methods.connect_db()
    collection = db["Channel_News_Asia"]

    EXIST_ARTICLES = set(i.get('link', i.get('Link')) for i in collection.find())

    page = 0
    n = 2

    for step in range(n):
        page += 1
        try:
            p = await browser.get(f"{main_url}{category_id}&page={page}")
            await p.maximize()
            print(f'Scrolling in the section {category}...')
        except:
            await browser.wait(2)
            p = await browser.get(f"{main_url}{category_id}&page={page}")
            await p.maximize()

        url_list = await get_article_links(p)
        # print(f'URLs: {url_list}')
        print(f'\nWorking on {category}, page {page}, scraping {len(url_list)} articles\n')

        for article_url in url_list:
            try:
                if article_url in EXIST_ARTICLES:
                    print('Article existed!!!\t', article_url)
                else:
                    title, author, content, date, utc_date_time = await extract_information(browser, article_url)
                    print(f'Extracted info: {content}')
                    data = {
                        'date': date,
                        'utc_date_time': utc_date_time,
                        'title': title,
                        'author': author,
                        'content': content,
                        'link': article_url,
                        'category': category
                    }
                    if content:
                        import_success = common_methods.import_into_db(data, collection)
                        if import_success:
                            EXIST_ARTICLES.add(article_url)
            except Exception as e:
                print('Fail!!!\t', article_url)
                print(e)

async def main():
    global main_url
    main_url = 'https://www.channelnewsasia.com/'
    browser = await uc.start(sandbox=False)

    category_dict = {
        'Business': 'search?categories%5B0%5D=Business',
        'Asia': 'search?categories%5B0%5D=Asia',
        'Singapore': 'search?categories%5B0%5D=Singapore',
        'Sustainability': 'search?categories%5B0%5D=Sustainability',
        'World': 'search?categories%5B0%5D=World',
        'CNA Lifestyle': 'search?categories%5B0%5D=CNA%20Lifestyle',
        'Trending': 'search?categories%5B0%5D=Trending',
        'Health and Matters': 'search?categories%5B0%5D=Health%20Matters',
        "CNA Luxury": "search?categories%5B0%5D=CNA%20Luxury"
    }

    # tasks = [do_scrapy(driver, category, category_id) for category, category_id in category_dict.items()]
    for category, category_id in category_dict.items():
        await do_scrapy(browser, category, category_id)
    await browser.stop()

if __name__ == '__main__':
    uc.loop().run_until_complete(main())
