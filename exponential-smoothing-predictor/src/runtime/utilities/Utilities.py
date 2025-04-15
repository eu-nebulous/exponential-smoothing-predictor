# Copyright (c) 2023 Institute of Communication and Computer Systems
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.        

import pathlib
#from morphemic.dataset import DatasetMaker
import datetime
import logging,os
import json
from jproperties import PropertyTuple, Properties
from influxdb_client import InfluxDBClient

from runtime.operational_status.EsPredictorState import EsPredictorState
from runtime.utilities.InfluxDBConnector import InfluxDBConnector


class Utilities:

    @staticmethod
    def print_with_time(x):
        now = datetime.datetime.now()
        string_to_print = "["+now.strftime('%Y-%m-%d %H:%M:%S')+"] "+str(x)
        print(string_to_print)
        return string_to_print

    
    @staticmethod
    def load_configuration():
        with open(EsPredictorState.configuration_file_location, 'rb') as config_file:
            configuration = Properties()
            configuration.load(config_file) 
            
            def get_config_value(key):
                """
                Retrieves a configuration value, prioritizing environment variables over configuration file values.
                """
                return os.getenv(key, configuration.get(key).data)

            EsPredictorState.publish_predictions_as_preliminary =  get_config_value("publish_preliminary_predictions").lower() in ('true', '1', 't')
            #prediction_horizon = configuration_details.get("prediction_horizon")
            EsPredictorState.number_of_days_to_use_data_from = int(get_config_value("number_of_days_to_use_data_from"))
            EsPredictorState.prediction_processing_time_safety_margin_seconds = int(get_config_value("prediction_processing_time_safety_margin_seconds"))
            EsPredictorState.testing_prediction_functionality = get_config_value("testing_prediction_functionality").lower() in ('true', '1', 't')
            EsPredictorState.path_to_datasets = get_config_value("path_to_datasets")
            EsPredictorState.broker_address = get_config_value("broker_address")
            EsPredictorState.broker_port = int(get_config_value("broker_port"))
            EsPredictorState.broker_username = get_config_value("broker_username")
            EsPredictorState.broker_password = get_config_value("broker_password")

            EsPredictorState.influxdb_hostname = get_config_value("INFLUXDB_HOSTNAME")
            EsPredictorState.influxdb_port = int(get_config_value("INFLUXDB_PORT"))
            EsPredictorState.influxdb_username = get_config_value("INFLUXDB_USERNAME")
            EsPredictorState.influxdb_password = get_config_value("INFLUXDB_PASSWORD")
            EsPredictorState.influxdb_org = get_config_value("INFLUXDB_ORG")
        #This method accesses influx db to retrieve the most recent metric values.
            logging.debug("The configuration effective currently is the following\n "+Utilities.get_fields_and_values(EsPredictorState))

    @staticmethod
    def update_influxdb_organization_id():
        client = InfluxDBClient(url="http://" + EsPredictorState.influxdb_hostname + ":" + str(EsPredictorState.influxdb_port), token=EsPredictorState.influxdb_token)
        org_api = client.organizations_api()
        # List all organizations
        organizations = org_api.find_organizations()

        # Find the organization by name and print its ID
        for org in organizations:
            if org.name == EsPredictorState.influxdb_organization:
                logging.debug(f"Organization Name: {org.name}, ID: {org.id}")
                EsPredictorState.influxdb_organization_id = org.id
                break
    @staticmethod
    def fix_path_ending(path):
        if (path[-1] is os.sep):
            return path
        else:
            return path + os.sep

    @staticmethod
    def default_to_string(obj):
        return str(obj)
    @classmethod
    def get_fields_and_values(cls,object):
        #Returns those fields that do not start with __ (and their values)
        fields_values = {key: value for key, value in object.__dict__.items() if not key.startswith("__")}
        return json.dumps(fields_values,indent=4,default=cls.default_to_string)

