# Copyright (c) 2023 Institute of Communication and Computer Systems
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.        

import pathlib
#from morphemic.dataset import DatasetMaker
import datetime
import logging,os
from dateutil import parser
from influxdb_client import InfluxDBClient

from runtime.operational_status.EsPredictorState import EsPredictorState
from runtime.utilities.InfluxDBConnector import InfluxDBConnector


class Utilities:

    @staticmethod
    def print_with_time(x):
        now = datetime.datetime.now()
        print("["+now.strftime('%Y-%m-%d %H:%M:%S')+"] "+str(x))

    @staticmethod
    def load_configuration():
        with open(EsPredictorState.configuration_file_location, 'rb') as config_file:
            EsPredictorState.configuration_details.load(config_file)
            #prediction_horizon = configuration_details.get("prediction_horizon")
            EsPredictorState.number_of_days_to_use_data_from = int(EsPredictorState.configuration_details.get("number_of_days_to_use_data_from").data)
            EsPredictorState.prediction_processing_time_safety_margin_seconds = int(EsPredictorState.configuration_details.get("prediction_processing_time_safety_margin_seconds").data)
            EsPredictorState.testing_prediction_functionality = EsPredictorState.configuration_details.get("testing_prediction_functionality").data.lower() == "true"
            EsPredictorState.path_to_datasets = EsPredictorState.configuration_details.get("path_to_datasets").data
            EsPredictorState.broker_address = EsPredictorState.configuration_details.get("broker_address").data
            EsPredictorState.broker_port = int(EsPredictorState.configuration_details.get("broker_port").data)
            EsPredictorState.broker_username = EsPredictorState.configuration_details.get("broker_username").data
            EsPredictorState.broker_password = EsPredictorState.configuration_details.get("broker_password").data

            EsPredictorState.influxdb_hostname = EsPredictorState.configuration_details.get("INFLUXDB_HOSTNAME").data
            EsPredictorState.influxdb_port = int(EsPredictorState.configuration_details.get("INFLUXDB_PORT").data)
            EsPredictorState.influxdb_username = EsPredictorState.configuration_details.get("INFLUXDB_USERNAME").data
            EsPredictorState.influxdb_password = EsPredictorState.configuration_details.get("INFLUXDB_PASSWORD").data
            EsPredictorState.influxdb_org = EsPredictorState.configuration_details.get("INFLUXDB_ORG").data
        #This method accesses influx db to retrieve the most recent metric values.


    @staticmethod
    def update_influxdb_organization_id():
        client = InfluxDBClient(url="http://" + EsPredictorState.influxdb_hostname + ":" + str(EsPredictorState.influxdb_port), token=EsPredictorState.influxdb_token)
        org_api = client.organizations_api()
        # List all organizations
        organizations = org_api.find_organizations()

        # Find the organization by name and print its ID
        for org in organizations:
            if org.name == EsPredictorState.influxdb_organization:
                logging.info(f"Organization Name: {org.name}, ID: {org.id}")
                EsPredictorState.influxdb_organization_id = org.id
                break
    @staticmethod
    def fix_path_ending(path):
        if (path[-1] is os.sep):
            return path
        else:
            return path + os.sep
