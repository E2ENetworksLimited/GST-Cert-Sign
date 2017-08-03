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
import configparser
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

# open log file
log_file = open("logs/" + NOW_DATE_TIME + ".txt", 'w+')

# Get mandrill client or die
if not MANDRILL_CONFIG:
    client = mandrill.Mandrill(MANDRILL_TEST_KEY)
else:
    client = mandrill.Mandrill(MANDRILL_PRODUCTION_KEY)

# init prettyprinter & configparser
pp = pprint.PrettyPrinter(indent=4)


def print_local_config():
    print("TIME:", end="")
    print(NOW_DATE_TIME)
    print("BCC:", end="")
    print(BCC)
    print("MANDRILL PRODUCTION:", end="")
    print(MANDRILL_CONFIG)
    print("Batch Size:", PAGE_SIZE)
    flag = prompt_check(
        "Running for the following config. Continue?")
    return flag


def log(head, detail):
    log_entry = "[" + str(datetime.now())[0:20] + "]" + \
        '\t' + "[" + head + "]" + '\t' + "[" + detail + "]"
    log_file.write(log_entry)
    log_file.write("\n")


def log_object(object):
    log_file.write('\n' + '\'' * 100 + '\n')
    log_file.write(pp.pformat(object))
    log_file.write('\n' + '\'' * 100 + '\n')

# filter input IDs from invoice_details dict using output.csv


def filter_id_dict(invoice_numbers, invoice_details):
    removed_numbers = []
    invoice_numbers_array = invoice_numbers.strip().split(',')
    file = open(OUTPUT_FILE, 'r')
    processed_numbers_string = file.read()
    file.close()
    processed_numbers = processed_numbers_string.strip().split(',')
    processed_numbers.remove('start')

    for processed_number in processed_numbers:
        index = -1
        for i in range(0, len(invoice_details)):
            inv = invoice_details[i]
            if(inv['invoice_number'] == processed_number):
                index = i

        if(index != -1):
            del invoice_details[index]

    return processed_numbers

# filter input IDs using output.csv


def filter_ids(invoice_numbers):
    removed_numbers = []
    invoice_numbers_array = invoice_numbers.strip().split(',')
    file = open(OUTPUT_FILE, 'r')
    processed_numbers_string = file.read()
    file.close()
    processed_numbers = processed_numbers_string.strip().split(',')

    for invoice_number in invoice_numbers_array:
        if invoice_number in processed_numbers:
            removed_numbers.append(invoice_number)

    for removed_number in removed_numbers:
        invoice_numbers_array.remove(removed_number)

    id_dict = {'invoice_numbers_array': invoice_numbers_array,
               'removed_numbers': removed_numbers}

    return id_dict


# fetch invoice detail for a invoice_id array by invoice_id
def fetch_invoice_details_with_number(invoice_numbers):
    message = "Fetching invoice details for Numbers:" + \
        ','.join(invoice_numbers)
    print(message)
    log("STARTING FETCH", message)

    invoice_details = []

    del querystring['status']

    for invoice_number in invoice_numbers:
        querystring['invoice_number_contains'] = invoice_number

        try:
            response = requests.request("GET", INVOICES_API, headers=headers, params=querystring,
                                        timeout=30)
        except Exception as err:
            print("Connection failed")
            log("Connection to invoices API failed", str(err))
            invoice_detail = {}
            invoice_detail['invoice_number'] = invoice_number
            invoice_detail['exist'] = False
            invoice_details.append(invoice_detail)
            continue

        response_object = json.loads(response.text)
        try:
            invoices_array = response_object['invoices']
        except Exception:
            continue

        invoice_detail = {}
        if(len(invoices_array) == 0):
            print("Invoice does not exist")
            invoice_detail = {}
            invoice_detail['invoice_number'] = invoice_number
            invoice_detail['exist'] = False
            invoice_details.append(invoice_detail)
        else:
            invoices = invoices_array[0]
            invoice_detail = {}
            invoice_detail['exist'] = True
            invoice_detail['customer_id'] = invoices['customer_id']
            invoice_detail['invoice_id'] = invoices['invoice_id']
            invoice_detail['invoice_number'] = invoices['invoice_number']
            contact_details = fetch_contact_emails_from_customer_id(
                invoices['customer_id'])
            if contact_details is None:
                invoice_detail['emailing_list'] = None
                invoice_detail['template_type'] = None
            else:
                invoice_detail['emailing_list'] = contact_details[
                    'contact_emails']
                invoice_detail['template_type'] = contact_details[
                    'template_type']
            invoice_details.append(invoice_detail)

    message = "Fetching successful for Numbers:" + '-'.join(invoice_numbers)
    print(message)
    log("FETCH SUCCESSFUL", message)

    return invoice_details


def fetch_invoice_details(date_start, date_end, batch_size=200):
    message = "Fetching invoice details in range:" + date_start + " - " + date_end
    print(message)
    log("STARTING FETCH", message)

    querystring['date_start'] = date_start
    querystring['date_end'] = date_end
    querystring['per_page'] = batch_size
    try:
        response = requests.request(
            "GET", INVOICES_API, headers=headers, params=querystring, timeout=30)
    except Exception as err:
        print("Connection to invoice API failed")
        log("Connection to invoices API failed", str(err))
        exit()

    invoice_details = None
    response_object = json.loads(response.text)
    invoices_array = response_object['invoices']
    if(len(invoices_array) == 0):
        return None
    else:
        invoice_details = []
        index = 1
        for invoices in invoices_array:
            print("Fetching details for invoice number " + str(index) + ": ")
            print(invoices['invoice_number'])
            invoice_detail = {}
            invoice_detail['exist'] = True
            invoice_detail['customer_id'] = invoices['customer_id']
            invoice_detail['invoice_number'] = invoices['invoice_number']
            contact_details = fetch_contact_emails_from_customer_id(
                invoices['customer_id'])
            if contact_details is None:
                invoice_detail['emailing_list'] = []
                invoice_detail['template_type'] = None
                invoice_detail['invoice_id'] = None
            else:
                invoice_detail['emailing_list'] = contact_details[
                    'contact_emails']
                invoice_detail['template_type'] = contact_details[
                    'template_type']
                invoice_detail['invoice_id'] = invoices['invoice_id']
            # invoice_detail['template_type'] =
            invoice_details.append(invoice_detail)
            index += 1

    message = "Fetching successful in range:" + date_start + " - " + date_end
    print(message)
    log("FETCH SUCCESSFUL", message)

    return invoice_details


# fetch emails for a particular invoice and template type
def fetch_contact_emails_from_customer_id(customer_id):
    url = CONTACTS_API + customer_id
    response = None
    emails = None
    try:
        response = requests.request(
            "GET", url, headers=headers, params=querystring, timeout=30)
    except Exception as err:
        print("Connection to contacts API failed. Emailing list not fetched")
        log("Connection to contacts API failed", str(err))
        return None

    contact_response_object = json.loads(response.text)
    contact_data = contact_response_object['contact']
    company_name = contact_data['company_name']
    contact_persons = contact_data['contact_persons']
    emails = []
    for contact_person in contact_persons:
        name = ' '.join((contact_person['salutation'],
                         contact_person['first_name'], contact_person['last_name']))
        to = {
            'name': name,
            'email': contact_person['email'],
            'type': 'to',
            'first_name': contact_person['first_name'],
            'company_name': company_name
        }
        emails.append(to)

    default_templates = contact_data['default_templates']
    email_template = default_templates['invoice_email_template_name']

    return_dict = {'contact_emails': emails,
                   'template_type': email_template}

    return return_dict

# send emails to the email list


def send_mails(invoice, attachment):
    exist = invoice['exist']
    download = invoice['download']

    if not exist or not download:
        message = "Cannot send mail for number: " + invoice['invoice_number']
        message += " Exist:" + str(exist)
        message += " Download:" + str(download)
        print(message)
        log("MAIL NOT SENT", message)
        return None

    email_list = invoice['emailing_list']

    if email_list is None:
        log("NO EMAIL LIST", "email_list not found for:" +
            invoice['invoice_number'])
        invoice['emails_sent'] = False
        invoice['set_status'] = False
        return None

    try:
        company_name = email_list[0]['company_name']
    except Exception:
        log("Company name not found %s" %
            str(invoice['invoice_id']), "company name not found")
        company_name = "No Name"

    headers = {
        'Reply-To': REPLY_TO
    }

    bcc = {
        'email': BCC,
        'name': 'ZOHO-BOOKS',
        'type': 'bcc',
        'first_name': 'ZOHO-BOOKS',
        'customer_name': 'customer_name',
        'invoice_number': invoice['invoice_number'],
        'company_name': company_name
    }

    print("Emailing for:")
    print(invoice['invoice_number'])

    email_list.append(bcc)
    merge_vars = []
    template_contents = []
    for email in email_list:
        merge_var = {
            'rcpt': email['email'],
            'vars': [{'name': 'first_name', 'content': email['first_name']},
                     {'name': 'customer_name', 'content': email['name']},
                     {'name': 'invoice_number',
                         'content': invoice['invoice_number']},
                     {'name': 'company_name', 'content': email['company_name']}]
        }
        merge_vars.append(merge_var)
        template_contents.append(merge_var)

    message = {
        'from_name': FROM_NAME,
        'from_email': FROM_EMAIL,
        'headers': headers,
        'preserve_recipients': True,
        'merge': True,
        'merge_language': 'mailchimp',
        'merge_vars': merge_vars,
        'to': email_list,
        'signing_domain': SIGNING_DOMAIN,
        'attachments': [{'content': attachment,
                         'name': invoice['invoice_number'] + '.pdf',
                         'type': 'application/pdf'}]
    }

    template_name = MANDRILL_TEMPLATE_NAME
    message['subject'] = "*|company_name|* Invoice#: *|invoice_number|*"

    status_list = None
    try:
        status_list = []
        response_list = client.messages.send_template(template_name=template_name, message=message, async=False,
                                                      template_content=template_contents)

        for response in response_list:
            status_obj = {'email': response['email'],
                          'status': response['status']}
            status_list.append(status_obj)

        url = MARK_AS_SENT.replace("%s", invoice['invoice_id'])
        if MANDRILL_CONFIG:
            try:
                response = requests.request("POST", url,
                                            headers=headers, params=querystring, timeout=30)
                invoice['set_status'] = True
            except Exception as err:
                message = "Setting sent status failed for:" + \
                    invoice['invoice_number']
                log("FAILED SET STATUS", message)
                print(message)
                invoice['set_status'] = False
        else:
            invoice['set_status'] = False
            print("Not updating the status due to mandrill test mode")

        invoice['emails_sent'] = True

    except Exception as err:
        invoice['emails_sent'] = False
        log("MANDRILL ERROR", str(err))
        print("Error connecting to mandrill. Email for some contact could be empty.")
        log_file.seek(0)
        send_log(DEV_LOGS_EMAIL, log_file.read(), date_mode)
        return status_list

    return status_list

# send logs over email


def send_log(email, log_content, date_mode):
    if date_mode:
        message = "Sending logs to dev-alerts"
        print(message)

    to = [{'email': email,
           'name': 'dev-alert',
           'type': 'to'
           }]

    if date_mode:
        subject = 'Auto-mail script log run for date range'
    else:
        subject = 'Auto-mail script log run for ID range'

    message = {
        'from_name': FROM_NAME,
        'from_email': FROM_EMAIL,
        'text': log_content,
        'to': to,
        'signing_domain': SIGNING_DOMAIN
    }

    message['subject'] = subject
    try:
        response = client.messages.send(message=message, async=False)
    except Exception as err:
        log("MANDRILL ERROR IN SENDING LOGS", str(err))
        print("Error connecting to mandrill while sending logs")
        log_file.close()
        exit()


def prompt_check(message):
    c = ""
    while(c.lower() != 'y' or c.lower() != 'n'):
        print(message)
        c = input()
        if(c.lower() == 'y'):
            return True
        elif(c.lower() == 'n'):
            return False


def download_invoices(invoice_details):
    message = "Download starting in directory:" + NOW_DATE_TIME
    log("STARTING DOWNLOAD", message)
    print(message)

    dl_success_flag = True

    os.makedirs(('data/IN/' + NOW_DATE_TIME))

    querystring['accept'] = 'pdf'

    for invoice in invoice_details:
        if(invoice['exist']):
            id = invoice['invoice_id']
        else:
            print("Does not exist or details fetching had failed")
            invoice['download'] = False
            continue
        url = INVOICES_API + "/" + id
        download_file_path = os.path.join(
            "data/IN/", NOW_DATE_TIME, invoice['invoice_number'].replace('/', '-') + ".pdf")
        invoice['path'] = download_file_path
        try:
            response = requests.request("GET", url,
                                        headers=headers, params=querystring, stream=True, timeout=30)

            with open(download_file_path, 'wb') as fd:
                for chunk in response.iter_content(chunk_size=2000):
                    fd.write(chunk)

            print("Downloaded invoice_number: ")
            print(invoice['invoice_number'])

            invoice['download'] = True
        except Exception as err:
            print(err)
            print("Download failed")
            invoice['download'] = False
            log("DOWNLOAD ERROR:" +
                "[" + invoice['invoice_number'] + "]", str(err))
            dl_success_flag = False

    message = "Download successful in directory:" + NOW_DATE_TIME
    log("DOWNLOAD COMPLETE", message)
    print(message)

    return dl_success_flag


def check_attachment_files(invoice_details):
    attachStatus = True
    for invoice in invoice_details:
        signed_file_path = os.path.join('data/OUT/', NOW_DATE_TIME, invoice['invoice_number'].replace("/", "-")
                                        + "_signed.pdf")
        if(os.path.isfile(signed_file_path)):
            invoice['attachment'] = True
        else:
            attachStatus = False

    return attachStatus


def sign_pdfs(invoice_details, platform, jsignpdf_path, batch_size=100):
    sign_flag = True
    message = "Starting Signing"
    log("SIGNING START", message)
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

    command_base = command_base.replace("%password", CRYPTOKEY_PASSWORD)

    files = []
    index = 0
    for invoice in invoice_details:
        if invoice['download']:
            if "path" in invoice:
                file = os.path.dirname(os.path.abspath(
                    __file__)) + '/' + invoice['path']
                files.append(file)

        index += 1

    index = 0
    for i in range(0, len(files), batch_size):
        command = command_base
        file_slice = files[i:i + batch_size]
        file_paths = ",".join(file_slice)
        command = command.replace("__files__", file_paths)

        if (PLATFORM == "linux"):
            SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
            os.chdir(os.path.dirname(jsignpdf_path))

        command_array = command.split(" ")
        command_array[2] = command_array[2].replace("%path", jsignpdf_path)
        process = subprocess.Popen(command_array)
        process.communicate()[0]
        status = process.returncode

        if (PLATFORM == "linux"):
            os.chdir(SCRIPT_DIR)

        if not status:
            message = "Signing finished for batch:" + str(index)
            log("SIGNING FINISHED", message)
            print(message)
        else:
            message = "Possible errors for batch:" + str(index)
            log("SIGNING ERROR", message)
            print(message)
            sign_flag = False
        index += 1

    processed = index * batch_size
    if(processed < len(files)):
        command = command_base
        file_slice = files[processed:len(files)]
        file_paths = " ".join(file_slice)

        command = command.replace("__files__", file_paths)
        if (PLATFORM == "linux"):
            SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
            os.chdir(os.path.dirname(jsignpdf_path))

        command_array = command.split(" ")
        command_array[2] = command_array[2].replace("%path", jsignpdf_path)
        process = subprocess.Popen(command_array)
        process.communicate()[0]
        status = process.returncode

        if (PLATFORM == "linux"):
            os.chdir(SCRIPT_DIR)

        if not status:
            message = "Signing finished for batch:" + str(index + 1)
            log("SIGNING FINISHED", message)
            print(message)
        else:
            message = "Possible errors for batch:" + str(index + 1)
            log("SIGNING ERROR", message)
            print(message)
            sign_flag = False

    return sign_flag


'''
date_mode = False    Invoice ID
date_mode = True     Date Range
'''


def main():
    arg_p = argparse.ArgumentParser()
    arg_p.add_argument(
        "--date", help="[start-date(yyyy-mm-dd)] [end-date(yyyy-mm-dd)]", nargs='*')
    arg_p.add_argument("--numbers", help="comma separated values")
    args = arg_p.parse_args()

    if args.date is None and args.numbers is None:
        print("Please select a mode of operation")
        exit()

    flag = print_local_config()
    if not flag:
        print("Exiting")
        log_file.close()
        exit()

    invoice_details = None

    if(args.date is None and args.numbers is None):
        print("Please provide an operation mode")
    elif args.date is not None:
        date_mode = True

        if(len(args.date) == 0):
            start_date = BEG_MONTH_DATE
            end_date = TODAY_DATE
        else:
            if(len(args.date) < 2):
                start_date = BEG_MONTH_DATE
                end_date = args.date[0]

                try:
                    start_date_t = datetime.strptime(start_date, "%Y-%m-%d")
                    end_date_t = datetime.strptime(end_date, "%Y-%m-%d")
                    if(start_date > end_date):
                        print("Start date has to be earlier than end date")
                        exit()
                except ValueError:
                    print("Invalid dates passed")
                    exit()
            else:
                start_date = args.date[0]
                end_date = args.date[1]
                try:
                    start_date_t = datetime.strptime(start_date, "%Y-%m-%d")
                    end_date_t = datetime.strptime(end_date, "%Y-%m-%d")
                    if(start_date > end_date):
                        print("Start date has to be earlier than end date")
                        exit()
                except ValueError:
                    print("Invalid dates passed")
                    exit()

        message = "Starting auto-mailer in range:" + start_date + "-" + end_date
        print(message)
        log("START RUN", message)

        invoice_numberList = []
        invoice_details = fetch_invoice_details(
            start_date, end_date, PAGE_SIZE)
        if invoice_details is None:
            print("No unsent in this date range")
            log("NO INVOICES", "no unsent invoices in this date range")
            log_file.seek(0)
            send_log(DEV_LOGS_EMAIL, log_file.read(), date_mode)
            log_file.close()
            exit()

        for invoice in invoice_details:
            invoice_numberList.append(invoice['invoice_id'])

        invoice_numberstring = ','.join(invoice_numberList)
        removed_numbers = filter_id_dict(invoice_numberstring, invoice_details)

        if(len(removed_numbers) != 0):
            removed_numbers = ','.join(removed_numbers)
            log("REMOVED DUPLICATES", message)
            log_object(removed_numbers)
            print(message)

    elif args.numbers is not None:
        date_mode = False

        message = "Starting auto-mailer for Numbers:" + args.numbers
        print(message)
        log("START RUN", message)

        invoice_numbers = args.numbers
        filteredinvoice_numbers = filter_ids(invoice_numbers)

        if(len(filteredinvoice_numbers['removed_numbers']) != 0):
            removed_numbers = ','.join(
                filteredinvoice_numbers['removed_numbers'])
            message = "Removing duplicates:" + removed_numbers
            log("REMOVED DUPLICATES", message)
            log_object(removed_numbers)
            print(message)

        invoice_details = fetch_invoice_details_with_number(
            filteredinvoice_numbers['invoice_numbers_array'])

    if invoice_details is None:
        if(date_mode):
            message = "No Invoices in date range:" + start_date + " - " + end_date
        else:
            message = "No unsent invoices"

        print(message)
        log("NO INVOICES", message)
        exit()

    log_object(invoice_details)

    dlFlag = download_invoices(invoice_details)

    log_object(invoice_details)

    sign_status = sign_pdfs(invoice_details, PLATFORM, JSIGNPDF_PATH)

    log_object(invoice_details)

    attachment_status = check_attachment_files(invoice_details)

    log_object(invoice_details)

    if attachment_status:
        message = "All attachments found. Proceed with emailing? "
        message += "No turning back beyond this point type Y to proceed :"
        prompt_flag = prompt_check(message)
    else:
        message = "Some attachments missing. Proceed with emailing? "
        message += "No turning back beyond this point type Y to proceed :"
        prompt_flag = prompt_check(message)
    if not prompt_flag:
        print("ABORTING")
        log("USER ACTION", "Signing errors")
        log_file.seek(0)
        log_content = log_file.read()
        send_log(DEV_LOGS_EMAIL, log_content, date_mode)
        exit()

    if(date_mode):
        message = "Starting Mailing:" + start_date + " - " + end_date
    else:
        message = "Starting Mailing for ID:" + invoice_numbers
    print(message)
    log("START MAILING", message)

    # email and send success to output.csv simultaneously
    file = open(OUTPUT_FILE, 'a')
    for invoice in invoice_details:
        signed_file_path = os.path.join('data/OUT/', NOW_DATE_TIME, invoice['invoice_number'].replace("/", "-")
                                        + "_signed.pdf")
        if(os.path.isfile(signed_file_path)):
            attachmentFile = open(signed_file_path, "rb")
            attachment = base64.b64encode(attachmentFile.read())
            status_list = send_mails(invoice, attachment.decode('utf-8'))
            if status_list is None:
                invoice['status_list'] = None
            else:
                invoice['status_list'] = status_list
                if MANDRILL_CONFIG:
                    file.write(',')
                    file.write(invoice['invoice_number'])
        else:
            message = "Attachment not found" + invoice['invoice_number']
            print("Attachment not found:" + invoice['invoice_number'])
            log("ATTACHMENT MISSING", message)
            invoice['attachment'] = False
            invoice['emails_sent'] = False
            invoice['set_status'] = False

    # close the output.csv file
    file.close()

    if(date_mode):
        message = "Done sending emails. Logging report:" + start_date + " - " + end_date
    else:
        message = "Done sending emails. Logging report"

    print(message)
    log("EMAILING COMPLETE", message)

    log_object(invoice_details)
    log("FINISHING", "Updating last_run to:" + TODAY_DATE)

    # On successful run, update last_run in settings
    cp.set('INIT', 'last_run', TODAY_DATE)
    file = open('settings.ini', "r+")
    cp.write(file)
    file.close()

    log_file.seek(0)
    log_content = log_file.read()
    send_log(DEV_LOGS_EMAIL, log_content, date_mode)

    log_file.close()

    # write output.csv
    with open(os.path.join("data", "reports", NOW_DATE_TIME + ".csv"), 'w') as csvfile:

        fieldnames = [
            'invoice_id',
            'invoice_number',
            'customer_id',
            'path',
            'template_type',
            'exist',
            'download',
            'attachment',
            'emails_sent',
            'set_status'
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for invoice in invoice_details:
            if('status_list' in invoice):
                del invoice['status_list']

            if('emailing_list' in invoice):
                del invoice['emailing_list']

            writer.writerow(invoice)

    print("Find report in data/reports/", end="")
    print(NOW_DATE_TIME, end="")
    print(".csv")

if __name__ == '__main__':
    main()
