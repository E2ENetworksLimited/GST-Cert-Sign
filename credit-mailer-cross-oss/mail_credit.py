'''
Copyright 2017 E2E Networks
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

import os
import subprocess
import sys
import requests
import json
import mandrill
import base64
import pprint
from datetime import datetime
import os
import ntpath
import argparse
from config.local_config import *
import re
import csv

PLATFORM = check_platform()

if PLATFORM is None:
    print("Platform not supported")
    exit()

# init prettyprinter
pp = pprint.PrettyPrinter(indent=4)

# Initialize mandrill client
if not MANDRILL_CONFIG:
    client = mandrill.Mandrill(MANDRILL_TEST_KEY)
else:
    client = mandrill.Mandrill(MANDRILL_PRODUCTION_KEY)

# functions for appending log to file


def print_local_config():
    print("TIME:", end="")
    print(NOW_DATE_TIME)
    print("BCC:", end="")
    print(BCC)
    print("MANDRILL PRODUCTION:", end="")
    print(MANDRILL_CONFIG)
    flag = prompt_check("Running for the following config. Continue?")
    return flag


def log(head, detail, log_file):
    log_entry = "[" + str(datetime.now())[0:20] + "]" + \
        '\t' + "[" + head + "]" + '\t' + "[" + detail + "]"
    log_file.write(log_entry)
    log_file.write("\n")


def log_object(object, log_file):
    log_file.write('\n' + '\'' * 100 + '\n')
    log_file.write(pp.pformat(object))
    log_file.write('\n' + '\'' * 100 + '\n')


def finish(log_file):
    log_file.seek(0)
    log_content = log_file.read()
    send_log(DEV_LOGS_EMAIL, log_content, log_file)
    log_file.close()


# filter input IDs using output.csv


def filter_numbers(credit_numbers, output_file):
    file = open(output_file, 'r')
    processed_numbers_string = file.read()
    file.close()
    processed_numbers = processed_numbers_string.strip().split(',')
    for processed_number in processed_numbers:
        try:
            credit_numbers.remove(processed_number)
            print("Removing processed number:")
            print(processed_number)
        except ValueError:
            pass

    return credit_numbers


def fetch_credit_details_with_number(credit_numbers, log_file):
    if not len(credit_numbers):
        message = "Nothing to process"
        print(message)
        log("EMPTY LIST", message)
        finish(log_file)
        exit()

    message = "Fetching credit details for numbers"
    print(message)
    log("STARTING FETCH", message, log_file)

    credit_details = []

    for credit_number in credit_numbers:
        print("Fetching credit details for:")
        print(credit_number)

        credit_detail = {}
        credit_detail['credit_number'] = credit_number
        credit_detail['exist'] = False

        querystring['creditnote_number'] = credit_number.strip()

        try:
            response = requests.request(
                "GET",
                CREDIT_NOTE_API,
                headers=headers,
                params=querystring,
                timeout=30)
        except Exception as err:
            print("Connection failed")
            log("Connection to credits API failed", str(err))
            credit_details.append(credit_detail)
            continue

        response_object = json.loads(response.text)

        try:
            credits_array = response_object['creditnotes']
        except Exception as err:
            message = "Response incorrect from API" + credit_number
            print(message)
            log("API ERROR", str(err), log_file)
            credit_details.append(credit_detail)
            continue

        if (len(credits_array) == 0):
            message = "Credit does not exist:" + credit_number
            print(message)
            log("NOT EXIST", message, log_file)
            credit_details.append(credit_detail)
        else:
            credits = credits_array[0]
            credit_detail = {}
            credit_detail['exist'] = True
            credit_detail['customer_id'] = credits['customer_id']
            credit_detail['credit_id'] = credits['creditnote_id']
            credit_detail['credit_number'] = credits['creditnote_number']
            credit_detail['creditnote_total'] = credits['total']
            credit_detail['creditnote_date'] = credits['date']
            credit_detail['creditnote_currency_code'] = credits[
                'currency_code']
            email_list = fetch_contact_emails_from_customer_id(
                credits['customer_id'])
            if email_list is None:
                credit_detail['emailing_list'] = None
            else:
                credit_detail['emailing_list'] = email_list

            credit_details.append(credit_detail)

    message = "Fetching successful for Numbers"
    print(message)
    log("FETCH SUCCESSFUL", message, log_file)

    return credit_details


# fetch emails for a particular credit and template type


def fetch_contact_emails_from_customer_id(customer_id):
    url = CONTACTS_API + customer_id
    response = None
    emails = None
    try:
        response = requests.request(
            "GET", url, headers=headers, params=querystring, timeout=30)
    except Exception as err:
        print("Connection to contacts API failed. Emailing list not fetched")
        log("Connection to contacts API failed", str(err), log_file)
        return None

    contact_response_object = json.loads(response.text)
    contact_data = contact_response_object['contact']
    company_name = contact_data['company_name']
    contact_persons = contact_data['contact_persons']
    emails = []
    for contact_person in contact_persons:
        name = ' '.join(
            (contact_person['salutation'], contact_person['first_name'],
             contact_person['last_name']))
        to = {
            'name': name,
            'email': contact_person['email'],
            'type': 'to',
            'first_name': contact_person['first_name'],
            'company_name': company_name
        }
        emails.append(to)

    return emails


# send emails to the email list


def send_mails(credit_detail, attachment, log_file):
    exist = credit_detail['exist']
    download = credit_detail['download']
    # sign = credit['sign']

    if not exist or not download:
        message = "Cannot send mail for number: " + \
            credit_detail['credit_number']
        message += " Exist:" + str(exist)
        message += " Download:" + str(download)
        print(message)
        log("MAIL NOT SENT", message, log_file)
        return None

    email_list = credit_detail['emailing_list']

    if email_list is None:
        log("NO EMAIL LIST",
            "emailList not found for:" + credit_detail['credit_number'],
            log_file)
        credit_detail['emails_sent'] = False
        credit_detail['set_status'] = False
        return None

    try:
        company_name = email_list[0]['company_name']
    except Exception:
        log("Company name not found %s" % str(credit_detail['credit_id']),
            "company name not found", log_file)
        company_name = "No Name"

    headers = {'Reply-To': REPLY_TO}

    bcc = {
        'email': BCC,
        'name': 'ZOHO-BOOKS',
        'type': 'bcc',
        'first_name': 'ZOHO-BOOKS',
        'customer_name': 'customer_name',
        'creditnote_number': credit_detail['credit_number'],
        'company_name': company_name
    }

    print("Emailing for:")
    print(credit_detail['credit_number'])

    email_list.append(bcc)
    merge_vars = []
    template_contents = []
    for email in email_list:
        merge_var = {
            'rcpt':
            email['email'],
            'vars': [{
                'name': 'first_name',
                'content': email['first_name']
            }, {
                'name': 'customer_name',
                'content': email['name']
            }, {
                'name': 'creditnote_number',
                'content': credit_detail['credit_number']
            }, {
                'name': 'company_name',
                'content': email['company_name']
            }, {
                'name': 'creditnote_date',
                'content': credit_detail['creditnote_date']
            }, {
                'name': 'creditnote_total',
                'content': credit_detail['creditnote_total']
            }, {
                'name': 'creditnote_currency_code',
                'content': credit_detail['creditnote_currency_code']
            }]
        }
        merge_vars.append(merge_var)
        template_contents.append(merge_var)

    template_name = MANDRILL_TEMPLATE_NAME

    message = {
        'from_name':
        'XXXX',
        'from_email':
        FROM_EMAIL,
        'headers':
        headers,
        'preserve_recipients':
        True,
        'merge':
        True,
        'merge_language':
        'mailchimp',
        'merge_vars':
        merge_vars,
        'to':
        email_list,
        'signing_domain':
        'XXXX',
        'attachments': [{
            'content': attachment,
            'name': credit_detail['credit_number'] + '.pdf',
            'type': 'application/pdf'
        }]
    }

    message[
        'subject'] = "Credit Note from XXXX (Credit Note #: *|creditnote_number|*)"

    status_list = None
    try:
        status_list = []
        response_list = client.messages.send_template(
            template_name=template_name,
            message=message,
            async=False,
            template_content=template_contents)

        for response in response_list:
            status_obj = {
                'email': response['email'],
                'status': response['status']
            }
            status_list.append(status_obj)

    except Exception as err:
        print(err)
        credit_detail['emails_sent'] = False
        log("MANDRILL ERROR", str(err), log_file)
        print("MANDRILL ERROR for :" + credit_detail['credit_number'])
        return None

    return status_list


# send logs over email


def send_log(email, log_content, log_file):
    print("Sending Logs to Dev-Alerts")

    to = [{'email': email, 'name': 'dev-alerts', 'type': 'to'}]

    message = {
        'from_name': 'XXXX',
        'from_email': FROM_EMAIL,
        'text': log_content,
        'to': to,
        'signing_domain': 'XXXX',
    }

    message['subject'] = "Auto-credit mailer run"
    try:
        response = client.messages.send(message=message, async=False)
    except Exception as err:
        log("MANDRILL ERROR IN SENDING LOGS", str(err), log_file)
        print("Error connecting to mandrill while sending logs")
        log_file.close()
        exit()


def prompt_check(message):
    c = ""
    while (c.lower != 'y' or c.lower() != 'n'):
        print(message)
        c = input()
        if (c.lower() == 'y'):
            return True
        elif (c.lower() == 'n'):
            return False


def download_credits(credit_details, log_file):
    message = "Download starting in directory:" + NOW_DATE_TIME
    log("STARTING DOWNLOAD", message, log_file)
    print(message)

    os.makedirs(('data/IN/' + NOW_DATE_TIME))

    querystring['accept'] = 'pdf'

    for credit_detail in credit_details:
        if (credit_detail['exist']):
            id = credit_detail['credit_id']
        else:
            message = "Does not exist or details fetching had failed"
            print(message)
            log("DOWNLOAD ERROR", message, log_file)
            credit_detail['download'] = False
            continue

        url = CREDIT_NOTE_API + id
        download_file_path = os.path.join(
            "data/IN/", NOW_DATE_TIME,
            credit_detail['credit_number'].replace('/', '-') + ".pdf")
        credit_detail['path'] = download_file_path

        try:
            response = requests.request(
                "GET",
                url,
                headers=headers,
                params=querystring,
                stream=True,
                timeout=30)

            with open(download_file_path, 'wb') as fd:
                for chunk in response.iter_content(chunk_size=1000):
                    fd.write(chunk)

            print("Downloaded credit number: ")
            print(credit_detail['credit_number'])

            credit_detail['download'] = True
        except Exception as err:
            print(err)
            print("Download failed")
            credit_detail['download'] = False
            log("DOWNLOAD ERROR:" + "[" + credit_detail['credit_number'] + "]",
                str(err), log_file)
            continue

    message = "Download successful in directory:" + NOW_DATE_TIME
    log("DOWNLOAD COMPLETE", message, log_file)
    print(message)

    return credit_details


def check_attachment_files(credit_details, log_file):
    attach_status = True
    for credit_detail in credit_details:
        signed_file_path = os.path.join(
            'data/OUT/', NOW_DATE_TIME,
            credit_detail['credit_number'].replace("/", "-") + "_signed.pdf")
        if (os.path.isfile(signed_file_path)):
            credit_detail['attachment'] = True
        else:
            credit_detail['attachment'] = False
            attach_status = False

    return attach_status


def sign_pdfs(credit_details, platform, jsignpdf_path, log_file):
    message = "Starting Signing"
    log("SIGNING START", message, log_file)
    print(message)

    dir_path = os.path.join("data/OUT/", NOW_DATE_TIME)
    os.makedirs(dir_path)
    if (platform == "windows"):
        command_base = 'java -jar %path __files__ --out-directory ' + \
            os.path.join(os.path.dirname(os.path.abspath(__file__)), dir_path) + ' -kst WINDOWS-MY -ksp %password' +\
            ' -ha SHA256 --visible-signature -llx 400 -lly 625 -urx 600 -ury 695 -fs 8.0'
    else:
        command_base = 'java -jar %path'
        command_base += ' __files__ --out-directory ' +  \
            os.path.join(os.path.dirname(os.path.abspath(__file__)), dir_path) + \
            ' -kst pkcs11 -ksp %password -ha SHA256'
        command_base += ' --visible-signature -llx 400 -lly 625 -urx 600 -ury 695 -fs 8.0'

    files = []
    for credit_detail in credit_details:
        if credit_detail['download']:
            if not "path" in credit_detail:
                credit_detail['sign'] = False
                message = "Input file not found"
                print(message)
                log("SIGNING ERROR", message, log_file)
            else:
                file = os.path.abspath(credit_detail['path'])
                files.append(file)

    file_string = " ".join(files)
    command_base = command_base.replace("%password", CRYPTOKEY_PASSWORD)
    command = command_base.replace("__files__", file_string)

    if (PLATFORM == "linux"):
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        os.chdir(os.path.dirname(jsignpdf_path))

    command_array = command.split(" ")
    command_array[2] = command_array[2].replace("%path", JSIGNPDF_PATH)
    process = subprocess.Popen(command_array)
    process.communicate()[0]
    status = process.returncode

    if (PLATFORM == "linux"):
        os.chdir(SCRIPT_DIR)

    if not status:
        message = "Signing finished completely"
        log("SIGNING FINISHED", message, log_file)
        print(message)
    else:
        message = "Signing finished partially"
        log("SIGNING FINISHED", message, log_file)
        print(message)

    return credit_details


def main():
    # process args
    arg_p = argparse.ArgumentParser()
    arg_p.add_argument("--cn", help="Creditnote number")
    args = arg_p.parse_args()

    # open log file
    log_file = open("logs/" + NOW_DATE_TIME + ".txt", 'w+')

    flag = print_local_config()
    if not flag:
        print("Exiting")
        log_file.close()
        exit()

    if (args.cn is None):
        print("Please provide an input")
        exit()
    elif args.cn is not None:
        message = "Starting auto-mailer for Numbers:" + args.cn
        print(message)
        log("START RUN", message, log_file)

        credit_numbers = args.cn
        filtered_credit_numbers = filter_numbers(
            credit_numbers.split(","), OUTPUT_FILE)

    credit_details = fetch_credit_details_with_number(filtered_credit_numbers,
                                                      log_file)

    log_object(credit_details, log_file)

    credit_details = download_credits(credit_details, log_file)

    log_object(credit_details, log_file)

    credit_details = sign_pdfs(credit_details, PLATFORM, JSIGNPDF_PATH,
                               log_file)

    log_object(credit_details, log_file)

    attachment_status = check_attachment_files(credit_details, log_file)

    log_object(credit_details, log_file)

    if attachment_status:
        message = "All attachments found. Proceed with emailing?" + \
            "No turning back beyond this point type Y to proceed :"
        prompt_flag = prompt_check(message)
    else:
        message = "Some attachments not found. Proceed with emailing?" + \
            "No turning back beyond this point type Y to proceed :"
        log("ATTACHMENT ERROR", message, log_file)
        prompt_flag = prompt_check(message)

    if not prompt_flag:
        print("ABORTING")
        log("USER ACTION", "Signing errors")
        finish(log_file)
        exit()

    message = "Starting Mailing"
    print(message)
    log("START MAILING", message, log_file)

    # email and send success to output.csv simultaneously
    file = open(OUTPUT_FILE, 'a')
    for credit_detail in credit_details:
        signed_file_path = os.path.join(
            'data/OUT/', NOW_DATE_TIME,
            credit_detail['credit_number'].replace("/", "-") + "_signed.pdf")
        if (os.path.isfile(signed_file_path)):
            attachment_file = open(signed_file_path, "rb")
            attachment = base64.b64encode(attachment_file.read())
            status_list = send_mails(credit_detail,
                                     attachment.decode('utf-8'), log_file)
            if status_list is None:
                credit_detail['status_list'] = None
                credit_detail['emails_sent'] = False
            else:
                credit_detail['status_list'] = status_list
                credit_detail['emails_sent'] = True
                if MANDRILL_CONFIG:
                    file.write(',')
                    file.write(credit_detail['credit_number'])
        else:
            message = "Attachment not found" + credit_detail['credit_number']
            print("Attachment not found:" + credit_detail['credit_number'])
            log("ATTACHMENT MISSING", message)
            credit_detail['emails_sent'] = False

    # close the output.csv file
    file.close()

    message = "Done sending emails. Logging report"

    print(message)
    log("EMAILING COMPLETE", message, log_file)

    log_object(credit_details, log_file)
    log("FINISHING", "Updating LAST_RUN to:" + TODAY_DATE, log_file)

    # On successful run, update last_run in settings
    cp.set('INIT', 'LAST_RUN', TODAY_DATE)
    file = open('settings.ini', "r+")
    cp.write(file)
    file.close()

    finish(log_file)

    # write report
    with open(os.path.join("data", "reports", NOW_DATE_TIME + ".csv"),
              'w') as csvfile:

        fieldnames = [
            'credit_id', 'credit_number', 'customer_id', 'creditnote_date',
            'creditnote_total', 'creditnote_currency_code', 'path', 'exist',
            'download', 'attachment', 'emails_sent'
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for credit_detail in credit_details:
            if ('status_list' in credit_detail):
                del credit_detail['status_list']

            if ('emailing_list' in credit_detail):
                del credit_detail['emailing_list']

            writer.writerow(credit_detail)

    print("Find report in data/reports/", end="")
    print(NOW_DATE_TIME, end="")
    print(".csv")


if __name__ == "__main__":
    main()
