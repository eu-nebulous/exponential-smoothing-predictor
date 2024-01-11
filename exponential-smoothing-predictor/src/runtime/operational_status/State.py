# Copyright (c) 2023 Institute of Communication and Computer Systems
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.        

import threading
from jproperties import Properties

class State:
    """
    Fail-safe default values introduced below
    """

    prediction_data_filename = "default_application.csv"
    MONITORING_DATA_PREFIX = "monitoring"
    FORECASTING_CONTROL_PREFIX = "forecasting"

    #Used to create the dataset from the InfluxDB
    application_name = "default_application"
    influxdb_bucket = "nebulous"
    influxdb_organization = "nebulous"
    influxdb_token = "tzIfpbU9b77quyvN0yHIbWltSh1c1371-o9nl_wJYaeo5TWdk5txyxXhp2iaLVMvOvf020HnEEAkE0yy5AllKQ=="
    influxdb_dbname = "nebulous"
    influxdb_password = "adminadmin"
    influxdb_username = "admin"
    influxdb_port = 8086
    influxdb_hostname = "localhost"
    path_to_datasets = "./datasets"
    dataset_file_name = "exponential_smoothing_dataset.csv"
    number_of_days_to_use_data_from = 365

    #Forecaster variables
    metrics_to_predict = []
    epoch_start = 0
    next_prediction_time = 0
    previous_prediction = None
    configuration_file_location="prediction_configuration.properties"
    configuration_details = Properties()
    prediction_processing_time_safety_margin_seconds = 20
    disconnected = True
    disconnection_handler = threading.Condition()
    initial_metric_list_received = False
    testing_prediction_functionality = False
    total_time_intervals_to_predict = 8

    #Connection details
    subscribing_connector = None
    publishing_connector = None
    broker_publishers = []
    broker_consumers = []
    connector = None
    broker_address = "localhost"
    broker_port = 5672
    broker_username = "admin"
    broker_password = "admin"


    @staticmethod
    #TODO inspect State.connection
    def check_stale_connection():
        return (not State.subscribing_connector)
