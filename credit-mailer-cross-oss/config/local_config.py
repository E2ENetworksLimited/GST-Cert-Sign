from datetime import datetime
import configparser
import os
import platform

cp = configparser.ConfigParser()
try:
    cp.readfp(open('settings.ini', "r+"))
except Exception as err:
    print("Error reading settings.ini:" + str(err))
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
    AUTHTOKEN = cp.get('ZOHO', 'AUTHTOKEN')
    ORGANIZATION_ID = cp.get('ZOHO', 'ORGANIZATION_ID')
    MANDRILL_TEST_KEY = cp.get('MANDRILL', 'MANDRILL_TEST_KEY')
    MANDRILL_PRODUCTION_KEY = cp.get('MANDRILL', 'MANDRILL_PRODUCTION_KEY')
    MANDRILL_TEMPLATE_NAME = cp.get('MANDRILL', 'MANDRILL_TEMPLATE_NAME')
except:
    print("Error in settings.ini. Contact support")
    exit()

querystring = {
    "authtoken": AUTHTOKEN.strip(),
    "organization_id": ORGANIZATION_ID.strip()
}

OUTPUT_FILE = os.path.abspath(os.path.join("data", "output.csv"))

headers = {'cache-control': "no-cache", 'Accepts': 'application/json'}

CREDIT_NOTE_API = "https://books.zoho.com/api/v3/creditnotes/".strip()
CONTACTS_API = "https://books.zoho.com/api/v3/contacts/".strip()

# setup log file, download directory and decide start and end dates for
# script run
script_start_time = datetime.now()

year = str(script_start_time.year)
month = str(script_start_time.month).zfill(2)
day = str(script_start_time.day).zfill(2)
hour = str(script_start_time.hour).zfill(2)
minute = str(script_start_time.minute).zfill(2)
second = str(script_start_time.second).zfill(2)

TODAY_DATE = '-'.join((year, month, day))

# open log file
NOW_DATE_TIME = '-'.join((year, month, day)) + "_" + \
    '-'.join((hour, minute, second))

if (MANDRILL_PRODUCTION.lower() == "false"):
    MANDRILL_CONFIG = False
elif (MANDRILL_PRODUCTION.lower() == "true"):
    MANDRILL_CONFIG = True
else:
    print("Invalid state of mandrill in settings.ini")
    exit()

if (SIGN_ENABLE.lower() == "false"):
    SIGN_ENABLE = False
elif (SIGN_ENABLE.lower() == "true"):
    SIGN_ENABLE = True
else:
    print("Error in settings.ini. Contact support")
    exit()


def check_platform():
    PLATFORM = platform.system().lower().strip()
    if PLATFORM != "linux" and PLATFORM != "windows":
        return None
    else:
        return PLATFORM
