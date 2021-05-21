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


# TODO:
#   - monitoring alerts

import requests
import os
import sys
import json
import logging

# set dev mode if you don't have access to the api url.
devMode = True

state_file = "./data/state.json"
sub_dirs   = [ "logs", "data" ]

def writeJsonFile(data, output_file):
    print("Writing to file: " + output_file)
    open(output_file, 'w').write(json.dumps(data, sort_keys=True, indent=4))

def readJsonFile(input_file):
    print("Reading file: " + input_file)
    with open(input_file) as json_file:
        return json.load(json_file)

def tellSomeone(msg, printer_list):

    for printer in printer_list:
        log_msg = "{}\n Printer details:\n {}".format(msg, printer)
        print(log_msg)
        logging.info(log_msg)

def metaMonitoringAlert(error):
    log_msg = "There appears to be a problem with running the monitoring script:\n {}".format(error)
    print(log_msg)
    logging.error(log_msg)

if devMode:
    papercut_api_url = "http://localhost:8000/data/sample_data.json"

else:
    # update to use your papercut server api url for retrieving the json file.
    papercut_api_url = "http://server:port/api_uri"

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
    for sub_dir in sub_dirs:
        if not os.path.isdir(sub_dir):
            full_path = os.getcwd() + "/" + sub_dir
            print ("Creating directory: " + full_path)
            os.mkdir(full_path)

    # logging
    log_dir = os.path.join(os.getcwd(), 'logs')
    log_file = os.path.join(log_dir, 'loggity.log')
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
    e = sys.exc_info()[0]
    metaMonitoringAlert(e)
    raise
