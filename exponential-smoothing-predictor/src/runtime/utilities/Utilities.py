# Copyright (c) 2023 Institute of Communication and Computer Systems
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.        

import pathlib
#from morphemic.dataset import DatasetMaker
import datetime
import time,os
from dateutil import parser

from runtime.operational_status.State import State
from runtime.utilities.InfluxDBConnector import InfluxDBConnector


class DatasetMaker:
    pass


class Utilities:

    @staticmethod
    def print_with_time(x):
        now = datetime.datetime.now()
        print("["+now.strftime('%Y-%m-%d %H:%M:%S')+"] "+str(x))

    @staticmethod
    def load_configuration():
        with open(State.configuration_file_location,'rb') as config_file:
            State.configuration_details.load(config_file)
            #prediction_horizon = configuration_details.get("prediction_horizon")
            State.dataset_file_name = State.configuration_details.get("input_data_file").data
            State.number_of_days_to_use_data_from = int(State.configuration_details.get("number_of_days_to_use_data_from").data)
            State.prediction_processing_time_safety_margin_seconds = int(State.configuration_details.get("prediction_processing_time_safety_margin_seconds").data)
            State.testing_prediction_functionality = State.configuration_details.get("testing_prediction_functionality").data.lower() == "true"
            State.path_to_datasets = State.configuration_details.get("path_to_datasets").data
            State.broker_address = State.configuration_details.get("broker_address").data
            State.broker_port = int(State.configuration_details.get("broker_port").data)
            State.broker_username = State.configuration_details.get("broker_username").data
            State.broker_password = State.configuration_details.get("broker_password").data

            State.influxdb_hostname = State.configuration_details.get("INFLUXDB_HOSTNAME").data
            State.influxdb_port = int(State.configuration_details.get("INFLUXDB_PORT").data)
            State.influxdb_username = State.configuration_details.get("INFLUXDB_USERNAME").data
            State.influxdb_password = State.configuration_details.get("INFLUXDB_PASSWORD").data
            State.influxdb_dbname = State.configuration_details.get("INFLUXDB_DBNAME").data
            State.influxdb_org = State.configuration_details.get("INFLUXDB_ORG").data
            State.application_name = State.configuration_details.get("APP_NAME").data
        #This method accesses influx db to retrieve the most recent metric values.
    @staticmethod
    def update_monitoring_data():
        #query(metrics_to_predict,number_of_days_for_which_data_was_retrieved)
        #save_new_file()
        Utilities.print_with_time("Starting dataset creation process...")

        try:
            """
            Deprecated functionality to retrieve dataset creation details. Relevant functionality moved inside the load configuration method
            influxdb_hostname = os.environ.get("INFLUXDB_HOSTNAME","localhost")
            influxdb_port = int(os.environ.get("INFLUXDB_PORT","8086"))
            influxdb_username = os.environ.get("INFLUXDB_USERNAME","morphemic")
            influxdb_password = os.environ.get("INFLUXDB_PASSWORD","password")
            influxdb_dbname = os.environ.get("INFLUXDB_DBNAME","morphemic")
            influxdb_org = os.environ.get("INFLUXDB_ORG","morphemic")
            application_name = "default_application"
            """
            metric_names = ["cpu_usage","ram_usage"]
            for metric_name in State.metrics_to_predict:
                time_interval_to_get_data_for = str(State.number_of_days_to_use_data_from)+"d"
                print_data_from_db = True
                query_string = 'from(bucket: "'+State.influxdb_bucket+'")  |> range(start:-'+time_interval_to_get_data_for+')  |> filter(fn: (r) => r["_measurement"] == "'+metric_name+'")'
                influx_connector = InfluxDBConnector()
                print("performing query")
                current_time = time.time()
                result = influx_connector.client.query_api().query(query_string,State.influxdb_organization)
                elapsed_time = time.time()-current_time
                print("performed query, it took "+str(elapsed_time) + " seconds")
                #print(result.to_values())
                with open(Utilities.get_prediction_data_filename(State.configuration_file_location,metric_name), 'w') as file:
                    for table in result:
                        #print header row
                        file.write("Timestamp,ems_time,"+metric_name+"\r\n")
                        for record in table.records:
                            dt = parser.isoparse(str(record.get_time()))
                            epoch_time = int(dt.timestamp())
                            metric_value = record.get_value()
                            if(print_data_from_db):
                                file.write(str(epoch_time)+","+str(epoch_time)+","+str(metric_value)+"\r\n")
                                # Write the string data to the file



        except Exception as e:
            Utilities.print_with_time("Could not create new dataset as an exception was thrown")
            print(e)

    @staticmethod
    def get_prediction_data_filename(configuration_file_location,metric_name):
        from jproperties import Properties
        p = Properties()
        with open(configuration_file_location, "rb") as f:
            p.load(f, "utf-8")
            path_to_datasets, metadata = p["path_to_datasets"]
            application_name, metadata = p["application_name"]
            path_to_datasets = Utilities.fix_path_ending(path_to_datasets)
            return "" + str(path_to_datasets) + str(application_name) + "_"+metric_name+ ".csv"

    @staticmethod
    def fix_path_ending(path):
        if (path[-1] is os.sep):
            return path
        else:
            return path + os.sep
