from datetime import datetime
import configparser
import os
import platform


cp = configparser.ConfigParser()
try:
    cp.readfp(open('settings.ini', "r+"))
except Exception as err:
    print("Error reading settings.ini:" + str(err))
    log("LOG PARSE ERROR", str(err))
    exit()

try:
    MANDRILL_PRODUCTION = cp.get('CONFIG', 'MANDRILL_PRODUCTION')
    SIGN_ENABLE = cp.get('CONFIG', 'SIGN_ENABLE')
    JSIGNPDF_PATH = cp.get('CONFIG', 'JSIGNPDF_PATH')
    BCC = cp.get('CONFIG', 'BCC')
    REPLY_TO = cp.get('CONFIG', 'REPLY_TO')
    FROM_EMAIL = cp.get('CONFIG', 'FROM_EMAIL')
    FROM_NAME = cp.get('CONFIG', 'FROM_NAME')
    SIGNING_DOMAIN = cp.get('CONFIG', 'SIGNING_DOMAIN')
    DEV_LOGS_EMAIL = cp.get('CONFIG', 'DEV_LOGS_EMAIL')
    CRYPTOKEY_PASSWORD = cp.get('CONFIG', 'CRYPTOKEY_PASSWORD')
    PAGE_SIZE = cp.get('CONFIG', 'PAGE_SIZE')
    AUTHTOKEN = cp.get('ZOHO', 'AUTHTOKEN')
    ORGANIZATION_ID = cp.get('ZOHO', 'ORGANIZATION_ID')
    MANDRILL_TEST_KEY = cp.get('MANDRILL', 'MANDRILL_TEST_KEY')
    MANDRILL_PRODUCTION_KEY = cp.get('MANDRILL', 'MANDRILL_PRODUCTION_KEY')
    MANDRILL_TEMPLATE_NAME = cp.get('MANDRILL', 'MANDRILL_TEMPLATE_NAME')
except:
    print("Settings file seems to have been corrupted. Contact Support")
    exit()


querystring = {"authtoken": AUTHTOKEN,
               "organization_id": ORGANIZATION_ID, 'status': 'draft'}


OUTPUT_FILE = os.path.join("data", "output.csv")

headers = {
    'cache-control': "no-cache",
    'Accepts': 'application/json'
}

INVOICES_API = "https://books.zoho.com/api/v3/invoices".strip()
CONTACTS_API = "https://books.zoho.com/api/v3/contacts/".strip()
MARK_AS_SENT = "https://books.zoho.com/api/v3/invoices/%s/status/sent"

date_mode = None
start_date = None
end_date = None

# setup log file, download directory and decide start and end dates for
# script run
SCRIPT_START_TIME = datetime.now()

year = str(SCRIPT_START_TIME.year)
month = str(SCRIPT_START_TIME.month).zfill(2)
day = str(SCRIPT_START_TIME.day).zfill(2)
hour = str(SCRIPT_START_TIME.hour).zfill(2)
minute = str(SCRIPT_START_TIME.minute).zfill(2)
second = str(SCRIPT_START_TIME.second).zfill(2)

# open log file
NOW_DATE_TIME = '-'.join((year, month, day)) + "_" + \
    '-'.join((hour, minute, second))
TODAY_DATE = '-'.join((year, month, day))
BEG_MONTH_DATE = '-'.join((year, month, "01"))

if(MANDRILL_PRODUCTION.lower() == "false"):
    MANDRILL_CONFIG = False
elif(MANDRILL_PRODUCTION.lower() == "true"):
    MANDRILL_CONFIG = True
else:
    print("Invalid state of mandrill in settings.ini")
    exit()

if(SIGN_ENABLE.lower() == "false"):
    SIGN_ENABLE = False
elif(SIGN_ENABLE.lower() == "true"):
    SIGN_ENABLE = True
else:
    print("Invalid state of SIGN_ENABLEing in settings.ini")
    exit()


def check_platform():
    PLATFORM = platform.system().lower().strip()
    if PLATFORM != "linux" and PLATFORM != "windows":
        return None
    else:
        return PLATFORM
