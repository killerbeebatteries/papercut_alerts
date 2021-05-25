#!/usr/bin/env python3
#
# A script that can be run at regular intervals to check 
# It queries the papercut api, then compares it to a  previous reported state that is saved to a json file.
#
# It will alert on a change of state.
#

# Resources:
#   - https://www.papercut.com/kb/Main/TopTipsForUsingThePublicWebServicesAPI#using-the-api
#   - https://www.papercut.com/support/resources/manuals/ng-mf/common/topics/tools-monitor-system-health-api-overview.html
#   - https://docs.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook

import requests
import os
import sys
import json
import logging
import traceback

script_name = os.path.basename(__file__)

# set dev mode if you don't have access to the api url.
devMode = True

# enable/disable Microsoft Teams alerts.
teamsMessages = False
# Teams webhook url.
teams_webhook_url = "Please update."

if teamsMessages:
    import pymsteams

# enable/disable email alerts.
emailMessages = True

email_recipients = [ "user1@example.com", "user2@example.com" ]
email_sender = "friendly_monitoring@example.com"

data_path = "./data"
log_path = "./logs"
log_filename = "loggity.log"
state_filename = "state.json"
state_file = os.path.join(data_path, state_filename)
required_paths = [ data_path, log_path ]

if devMode:
    papercut_api_url = "http://localhost:8000/sample_data.json"
    smtp_host = "localhost"
    smtp_port = 1025

else:
    # update to use your papercut server api url for retrieving the json file.
    papercut_api_url = "http://server:port/api_uri"
    # update to use your local email relay.
    smtp_host = "mail.example.com"
    smtp_port = 25


def writeJsonFile(data, output_file):
    print("Writing to file: " + output_file)
    open(output_file, 'w').write(json.dumps(data, sort_keys=True, indent=4))

def readJsonFile(input_file):
    print("Reading file: " + input_file)
    with open(input_file) as json_file:
        return json.load(json_file)

def tellSomeone(msg, printer_list):
    log_msg = "{}\n Printer details:\n {}".format(msg, "\n".join(map(str, printer_list)))

    print(log_msg)
    logging.info(log_msg)

    if teamsMessages:
        sendTeamsMessage(log_msg)
            
    if emailMessages:
        if len(printer_list) > 1:
            subject = "Monitor alert: Multiple printers with errors."
        else:
            subject = "Monitor alert: {} has status of {}".format(printer["name"], printer["status"])

        sendEmail(log_msg, email_sender, email_recipients, subject, smtp_host, smtp_port)

def metaMonitoringAlert(error):
    log_msg = "There appears to be a problem with running the monitoring script:\n {}".format(error)
    print(log_msg)
    logging.error(log_msg)

    if teamsMessages:
        sendTeamsMessage(log_msg)

    if emailMessages:
        subject = "Monitor Alert: Script {} has triggered a meta monitoring error.".format(script_name)
        sendEmail(log_msg, email_sender, email_recipients, subject, smtp_host, smtp_port)

def sendTeamsMessage(msg):
    """
    Microsoft Teams API Message.
    Borrowed from: https://stackoverflow.com/questions/59371631/send-automated-messages-to-microsoft-teams-using-python
    """

    try:
        myTeamsMessage = pymsteams.connectorcard(teams_webhook_url)
        myTeamsMessage.text(msg)
        myTeamsMessage.send()
    except:
        e = sys.exc_info()[0]
        logging.error(e)

def sendEmail(msg, sender, recipients, subject, server, port):
    # helpful bit of code provided by elmato.
    import smtplib
    from email.mime.text import MIMEText

    email_msg = MIMEText(msg)

    email_msg["Subject"] = subject
    email_msg["From"]    = sender
    email_msg["To"]      = ", ".join(recipients)

    try:
        with smtplib.SMTP(server, port) as s:
            logging.info('Sending email to {}'.format(';'.join(recipients)))
            s.sendmail(sender, recipients, email_msg.as_string())
    except smtplib.SMTPException as e:
        logging.error(e)


# try to get data from papercut api
# if this fails, provide a meta alert, then exit.
try:
    r = requests.get(papercut_api_url, allow_redirects=True)

except requests.exceptions.RequestException as e:
    metaMonitoringAlert(e)
    raise SystemExit(e)

try:

    incoming_data = json.loads(r.content)
    current_erroring_printers  = incoming_data["printers"]["inError"]
    #print(incoming_data)

    # create our data and log directories if they don't exist
    for path in required_paths:
        if not os.path.isdir(path):
            print ("Creating directory: " + path)
            os.mkdir(path)

    # logging
    log_file = os.path.join(log_path, log_filename)
    log_line_format = '%(asctime)s - %(levelname)s - %(message)s'
    log_date_format = '%Y/%m/%d %H:%M:%S'

    logging.root.handlers = []
    logging.basicConfig(
        format=log_line_format,
        datefmt = log_date_format,
        handlers = [
        logging.FileHandler(log_file),
        logging.StreamHandler()
        ],
        level=logging.INFO
    )

    # if the state file exists, load it into a variable.
    if os.path.isfile(state_file):
        previous_data = readJsonFile(state_file)
        previous_erroring_printers = previous_data["printers"]["inError"]
        #print(previous_data)


        for current_printer in current_erroring_printers:
            name   = current_printer["name"]
            status = current_printer["status"]
            printerFound = False
            printerStatusMatch = False

            # if the erroring printer exists in our state file and the status error matches, assume we've already
            # alerted for this printer error previously.
            for previous_printer in previous_erroring_printers:
                if name == previous_printer["name"]:
                    printerFound = True
                    if status == previous_printer["status"]:
                        printerStatusMatch = True
                        print("Printer exists: " + name)
                        continue

            # if the printer isn't in the previous erroring printer list, we can assume it's a new error.
            if not printerFound:
                msg = "It appears we have a printer with a new error."
                tellSomeone(msg, [current_printer])

            # report error state change
            if not printerStatusMatch:
                msg = "It appears the error state has changed."
                tellSomeone(msg, [current_printer])

        # see if we have any printer records in our previous erroring printer list that are not in our current
        # erroring list.
        for previous_printer in previous_erroring_printers:
            printerStaleRecord = True

            for current_printer in current_erroring_printers:
                if current_printer["name"] == previous_printer["name"]:
                    printerStaleRecord = False

            if printerStaleRecord:
                msg = "It looks like a printer that was listed as having errors previously has been removed from the list."
                tellSomeone(msg, [previous_printer])

    else:
        msg = "No previous state file exists, so we'll create one."
        logging.error(msg)
        writeJsonFile(incoming_data, state_file)
        # assume we haven't alerted for the current list of erroring printers. Send now.
        msg = "New printer error(s) found."
        tellSomeone(msg, current_erroring_printers)

    # REMOVE: testing stale printer data functionality.
    #incoming_data["printers"]["inError"].append({"name": "org1-anotherprinter", "status": "OFFLINE"})

    # we then save the current state, overwriting the previous state.
    writeJsonFile(incoming_data, state_file)

except:
    #e = sys.exc_info()[0]
    e = traceback.format_exc()
    metaMonitoringAlert(e)
    raise
