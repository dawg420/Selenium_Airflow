from pymongo import MongoClient
# from random_user_agent.user_agent import UserAgent
# from random_user_agent.params import SoftwareName, OperatingSystem
import time
import uuid
import bson
from bson.binary import UuidRepresentation
# import undetected_chromedriver as uc
import pytz
import datetime
# from seleniumbase import Driver
from pymongo.errors import DuplicateKeyError

proxy_host = "squid"
proxy_port = 3128
proxy_login = "mylogin"
proxy_pass = "mypassword"

def connect_db():
    DB_URI = 'mongodb://crinlp:123@10.230.252.3:27017/?authSource=admin&readPreference=primary&appname=MongoDB%20Compass&ssl=false' ## Please set your own database here
    client = MongoClient(DB_URI)
    db = client.crinlp
    return db

def import_into_db(data, collection):
    """
    :param data: dict - output dictionary
    :param collection: str - name of the collection in mongodb
    :return: bool - True/False
    """
    current_date = time.strftime('%Y-%m-%d', time.localtime(time.time()))
    record = dict()

    _id = uuid.uuid3(uuid.NAMESPACE_DNS, data['title']+data['date'])
    _id = bson.Binary.from_uuid(_id, uuid_representation=UuidRepresentation.PYTHON_LEGACY)
    record["_id"]           = _id
    record["Date"]          = data['date']
    record["UTC_datetime"]  = data['utc_date_time']
    record["Title"]         = data['title']
    record["Author"]        = data['author']
    record["Content"]       = data['content']
    record["Category"]      = data['category']
    record["Link"]          = data['link']
    record['Processed']     = 0
    record["Storage_date"]  = current_date

    try:
        collection.insert_one(record)
        print(f"Inserted article: {data['title']}\n{data['link']}\n")
        return True

    except DuplicateKeyError as e:
        print(f"Duplicate article: {data['title']}\n{data['link']}\n")
        return False

    except Exception as e:
        print(f"Unexpected error inserting article: {data['title']}\n{data['link']}\n")
        print(e)
        return False


# def get_driver(isHeadless=False):
#     driver = Driver(uc=True, headless2=isHeadless)
#     return driver

# def get_user_agent():
#     """
#     Description: Use UserAgent to create random user agent
#     Input: None
#     Output: String - user agent
#     """
#     software_names = [SoftwareName.CHROME.value, SoftwareName.FIREFOX.value, SoftwareName.EDGE.value, SoftwareName.OPERA.value]
#     operating_systems = [OperatingSystem.UNIX.value, OperatingSystem.WINDOWS.value, OperatingSystem.LINUX.value, OperatingSystem.MAC.value]
#     user_agent_rotator = UserAgent(software_names=software_names, operating_systems=operating_systems, limit=1000)
#     # Get list of user agents.
#     user_agents = user_agent_rotator.get_user_agents()
#     # Get Random User Agent String.
#     user_agent = user_agent_rotator.get_random_user_agent()
#     return user_agent

# def generate_header(COOKIES):
#     """
#     Description: generate header randomly
#     Input: str - COOKIES;
#     Output: dict - header
#     """
#     header = {
#         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
#         'User-Agent': get_user_agent(),
#         'cookie': COOKIES
#     }
#     return header
def convert_LocalToUtc_Date(Date, time_zone=None, input_time_zone=None):
    """
    :param Date: str - Date input scrap from article
    :param time_zone: str - Timezone that scrap from article
    :param input_time_zone: str - Manual input for Timezone
    :return: date - UTC DateTime
    """
    #check your timezone using pytz.all_timezones
    if input_time_zone is None:

        if time_zone == "ET":
            input_time_zone = "US/Eastern"
        elif time_zone == "UTC":
            input_time_zone = "UTC"
        elif time_zone == "WIB":
            input_time_zone = "Asia/Jakarta"
        elif time_zone == "JST":
            input_time_zone = "Asia/Tokyo"

    local = pytz.timezone(input_time_zone)
    date = datetime.datetime.strptime(Date, "%Y-%m-%d %H:%M:%S")
    local_dt = local.localize(date, is_dst=None)
    utc_dt = local_dt.astimezone(pytz.utc)

    return utc_dt.strftime("%Y-%m-%d %H:%M:%S")