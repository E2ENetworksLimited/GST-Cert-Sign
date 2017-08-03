# Goals

- Digitally sign invoices for GST compliance
- Mail signed invoices to customers
- Should work for single or batch invoices

# Prerequisites

- JRE 1.6 or higher
- [JSignPdf 1.6.1] (http://jsignpdf.sourceforge.net/)
- Python 3.x
- Cryto Key drivers
- Python modules (requests, pprint, mandrill, configparser)
- Mandrill registration is necessary to send mail using the Mandrill service
- ZOHO registration as an invoice management service

# Supported OS

- Linux
- Windows 7 or higher

# Setup
- Install your CryptoKey drivers
- Install JSignPdf on windows or download zip package on linux
- Unzip each of the zip files in different filesystem locations
- Open settings.ini and update it accordingly

## Parameters in settings.ini
- page_size
  - This parameter decides how many entries with be processed in a batch in one run
- mandrill_production
  - Emails will actually be sent only if this is true
- jsignpdf_path
  - Path to the jsignpdf.jar according to your installation
- cryptokey_password
  - Password to your cryptokey
- bcc
  - Email to which all invoices will be blind carbon copied to keep track of sent invoices
- reply_to
  - (Reply to) for emails sent to customers
- from_email
  - (From email) for emails sent to customers
- dev_logs_email
  - Logs sent to an email for developer's reference

- authtoken
  - Authtoken for ZOHO account to be used
- organization_id
  - Organization ID for ZOHO account to be used

- mandrill_production_key
  - Production key for mandrill account
- mandrill_test_key
  - Test key for mandrill mode
- mandrill_template_name
  - Template to be used for sending emails in mandrill admin


# Usage

## Invoice signing and mailing script

- Run of beginning of current month to today

  - python mailInvoice.py

- Run for beginning of current month to the date passed

  - python mailInvoice.py --date [end-date(yyyy-mm-dd)]

- Run for a date range

  - python mailInvoice.py --date [start-date(yyyy-mm-dd)] [end-date(yyyy-mm-dd)]

- Run for specific Invoice Numbers

  - python mailInvoice.py --numbers [comma separated numbers]

## Credit note signing and sending script

- python mailCredit.py --cn [comma separated credit note numbers]

# Disk files and Logs
Data folder is of interest to the end user. It has 3 directories:-
- IN
  - This contains directories where the invoices are downloaded by the script itself.
- OUT
  - This contains corresponding directories to IN directories where digitally signed invoices are stored reports
- reports
  - This contains reports in CSV format for reference that can used to view if the emails were downloaded, signed and sent
- output.csv
  - This is a layer of protection against duplication. ID's for credit notes or invoices on successful processing are pushed to this file to filter out duplicates on further runs.

# Limitations
- Invoice mailer
  - When emails are sent, the call to mark invoices can fail and that requires manual marking on ZOHO
  - If there is a blank email for a contact list of an invoice, the mails won't be sent for that invoice

- Credit mailer
  - There is no provision to mark sent credit notes as closed. Requires manual demarcation.
  - If there is a blank email for a contact list of an invoice, the mails won't be sent for that invoice

# Copyright & Licence

**(C) 2017 E2E Networks**

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
