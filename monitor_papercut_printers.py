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
#   - track state
#   - monitoring alerts
#   - logging

import requests
import os
import sys
import json

# set dev mode if you don't have access to the api url.
devMode = True

state_file = "./data/state.json"
sub_dirs   = [ "logs", "data" ]

def writeJsonFile(data, output_file):
    print("Writing to file: " + output_file)
    open(output_file, 'w').write(json.dumps(data))

def readJsonFile(input_file):
    print("Reading file: " + input_file)
    with open(input_file) as json_file:
        return json.load(json_file)

def tellSomeone(error):
    print("It appears we have an error with:\n {}".format(error))

def metaMonitoringAlert(error):
    print("There appears to be a problem with running the monitoring script:\n {}".format(error))

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
    print(incoming_data)

    # create our data and log directories if they don't exist
    for sub_dir in sub_dirs:
        if not os.path.isdir(sub_dir):
            full_path = os.getcwd() + "/" + sub_dir
            print ("Creating directory: " + full_path)
            os.mkdir(full_path)


    # if the state file exists, load it into a variable.
    if os.path.isfile(state_file):
        previous_data = readJsonFile(state_file)
        print(previous_data)

        current_erroring_printers  = incoming_data["printers"]["inError"]
        previous_erroring_printers = previous_data["printers"]["inError"]

        for current_printer in current_erroring_printers:
            name   = current_printer["name"]
            status = current_printer["status"]

            # if the erroring printer exists in our state file and the status error matches, assume we've already
            # alerted for this printer error previously.
            if name in previous_erroring_printers:
                if status == previous_erroring_printers[name]["status"]:
                    continue
                else:
                    tellSomeone(current_printer)
            # if the printer isn't in the previous erroring printer list, we can assume it's a new error.
            else:
                tellSomeone(current_printer)

    else:
        print("No previous state file exists, so we'll create one and exit.")
        writeJsonFile(incoming_data, state_file)
        raise SystemExit()

    # we then save the current state, overwriting the previous state.
    writeJsonFile(incoming_data, state_file)

except:
    e = sys.exc_info()[0]
    metaMonitoringAlert(e)
    raise
