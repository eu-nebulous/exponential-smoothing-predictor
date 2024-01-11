# Copyright (c) 2023 Institute of Communication and Computer Systems
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.        

import datetime
import json
import threading
import time
import os, sys
import multiprocessing
import traceback
from subprocess import PIPE, run
from runtime.exn import core

import logging
from runtime.exn import connector
from runtime.predictions.Prediction import Prediction
from runtime.operational_status.State import State
from runtime.utilities.PredictionPublisher import PredictionPublisher
from runtime.utilities.Utilities import Utilities
print_with_time = Utilities.print_with_time






def predict_attribute(attribute, configuration_file_location,next_prediction_time):

    prediction_confidence_interval_produced = False
    prediction_value_produced = False
    prediction_valid = False
    #os.chdir(os.path.dirname(configuration_file_location))
    State.prediction_data_filename = Utilities.get_prediction_data_filename(configuration_file_location,attribute)

    from sys import platform
    if State.testing_prediction_functionality:
        print_with_time("Testing, so output will be based on the horizon setting from the properties file and the last timestamp in the data")
        print_with_time("Issuing command: Rscript forecasting_real_workload.R "+str(State.prediction_data_filename)+" "+attribute)

        # Windows
        if platform == "win32":
            command = ['Rscript', 'forecasting_real_workload.R', State.prediction_data_filename, attribute]
        # linux
        elif platform == "linux" or platform == "linux2":
            command = ["Rscript forecasting_real_workload.R "+str(State.prediction_data_filename) + " "+ str(attribute)]
        #Choosing the solution of linux
        else:
            command = ["Rscript forecasting_real_workload.R "+str(State.prediction_data_filename) + " "+ str(attribute)]
    else:
        print_with_time("The current directory is "+os.path.abspath(os.getcwd()))
        print_with_time("Issuing command: Rscript forecasting_real_workload.R "+str(State.prediction_data_filename)+" "+attribute+" "+next_prediction_time)

        # Windows
        if platform == "win32":
            command = ['Rscript', 'forecasting_real_workload.R', State.prediction_data_filename, attribute, next_prediction_time]
        # Linux
        elif platform == "linux" or platform == "linux2":
            command = ["Rscript forecasting_real_workload.R "+str(State.prediction_data_filename) + " "+ str(attribute)+" "+str(next_prediction_time) + " 2>&1"]
        #Choosing the solution of linux
        else:
            command = ["Rscript forecasting_real_workload.R "+str(State.prediction_data_filename) + " "+ str(attribute)+" "+str(next_prediction_time)]

    process_output = run(command, shell=True, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    if (process_output.stdout==""):
        print_with_time("Empty output from R predictions - the error output is the following:")
        print(process_output.stderr) #There was an error during the calculation of the predicted value

    process_output_string_list = process_output.stdout.replace("[1] ", "").replace("\"", "").split()
    prediction_value = 0
    prediction_confidence_interval = "-10000000000000000000000000,10000000000000000000000000"
    prediction_mae = 0
    prediction_mse = 0
    prediction_mape = 0
    prediction_smape = 0
    for string in process_output_string_list:
        if (string.startswith("Prediction:")):
            prediction_value = string.replace("Prediction:", "")
            prediction_value_produced = True
        if (string.startswith("Confidence_interval:")):
            prediction_confidence_interval = string.replace("Confidence_interval:", "")
            prediction_confidence_interval_produced = True
        elif (string.startswith("mae:")):
            prediction_mae = string.replace("mae:", "")
        elif (string.startswith("mse:")):
            prediction_mse = string.replace("mse:", "")
        elif (string.startswith("mape:")):
            prediction_mape = string.replace("mape:", "")
        elif (string.startswith("smape:")):
            prediction_smape = string.replace("smape:", "")
    if (prediction_confidence_interval_produced and prediction_value_produced):
        prediction_valid = True
        print_with_time("The prediction for attribute " + attribute + " is " + str(prediction_value)+ " and the confidence interval is "+prediction_confidence_interval)
    else:
        print_with_time("There was an error during the calculation of the predicted value for "+str(attribute)+", the error log follows")
        print_with_time(process_output.stdout)

    output_prediction = Prediction(prediction_value, prediction_confidence_interval,prediction_valid,prediction_mae,prediction_mse,prediction_mape,prediction_smape)
    return output_prediction


def predict_attributes(attributes,next_prediction_time):
    pool = multiprocessing.Pool(len(attributes))
    print_with_time("Prediction thread pool size set to " + str(len(attributes)))
    attribute_predictions = {}

    for attribute in attributes:
        print_with_time("Starting " + attribute + " prediction thread")
        start_time = time.time()
        attribute_predictions[attribute] = pool.apply_async(predict_attribute, args=[attribute, State.configuration_file_location,str(next_prediction_time)])
        #attribute_predictions[attribute] = pool.apply_async(predict_attribute, args=[attribute, configuration_file_location,str(next_prediction_time)]).get()

    for attribute in attributes:
        attribute_predictions[attribute] = attribute_predictions[attribute].get() #get the results of the processing
        attribute_predictions[attribute].set_last_prediction_time_needed(int(time.time() - start_time))
        #prediction_time_needed[attribute])

    pool.close()
    pool.join()
    return attribute_predictions


def update_prediction_time(epoch_start,prediction_horizon,maximum_time_for_prediction):
    current_time = time.time()
    prediction_intervals_since_epoch = ((current_time - epoch_start)//prediction_horizon)
    estimated_time_after_prediction = current_time+maximum_time_for_prediction
    earliest_time_to_predict_at = epoch_start + (prediction_intervals_since_epoch+1)*prediction_horizon #these predictions will concern the next prediction interval

    if (estimated_time_after_prediction > earliest_time_to_predict_at ):
        future_prediction_time_factor = 1+(estimated_time_after_prediction-earliest_time_to_predict_at)//prediction_horizon
        prediction_time = earliest_time_to_predict_at+ future_prediction_time_factor*prediction_horizon
        print_with_time("Due to slowness of the prediction, skipping next time point for prediction (prediction at " + str(earliest_time_to_predict_at-prediction_horizon)+" for "+ str(earliest_time_to_predict_at)+") and targeting "+str(future_prediction_time_factor)+" intervals ahead (prediction at time point "+str(prediction_time-prediction_horizon)+" for "+ str(prediction_time)+")")
    else:
        prediction_time = earliest_time_to_predict_at + prediction_horizon
    print_with_time("Time is now "+str(current_time)+" and next prediction batch starts with prediction for time "+str(prediction_time))
    return prediction_time


def calculate_and_publish_predictions(prediction_horizon,maximum_time_required_for_prediction):
    while Bootstrap.start_forecasting:
        print_with_time("Using " + State.configuration_file_location + " for configuration details...")
        State.next_prediction_time = update_prediction_time(State.epoch_start, prediction_horizon,maximum_time_required_for_prediction)

        for attribute in State.metrics_to_predict:
            if ((State.previous_prediction is not None) and (State.previous_prediction[attribute] is not None) and (State.previous_prediction[attribute].last_prediction_time_needed>maximum_time_required_for_prediction)):
                maximum_time_required_for_prediction = State.previous_prediction[attribute].last_prediction_time_needed

        #Below we subtract one reconfiguration interval, as we cannot send a prediction for a time point later than one prediction_horizon interval
        wait_time = State.next_prediction_time - prediction_horizon - time.time()
        print_with_time("Waiting for "+str((int(wait_time*100))/100)+" seconds, until time "+datetime.datetime.fromtimestamp(State.next_prediction_time - prediction_horizon).strftime('%Y-%m-%d %H:%M:%S'))
        if (wait_time>0):
            time.sleep(wait_time)
            if(not Bootstrap.start_forecasting):
                break

        Utilities.load_configuration()
        Utilities.update_monitoring_data()
        first_prediction = None
        for prediction_index in range(0,State.total_time_intervals_to_predict):
            prediction_time = int(State.next_prediction_time)+prediction_index*prediction_horizon
            try:
                print_with_time ("Initiating predictions for all metrics for next_prediction_time, which is "+str(State.next_prediction_time))
                prediction = predict_attributes(State.metrics_to_predict,prediction_time)
                if (prediction_time == int(State.next_prediction_time)):
                    first_prediction = prediction
            except Exception as e:
                print_with_time("Could not create a prediction for some or all of the metrics for time point "+str(State.next_prediction_time)+", proceeding to next prediction time. However, "+str(prediction_index)+" predictions were produced (out of the configured "+State.total_time_intervals_to_predict+"). The encountered exception trace follows:")
                print(e)
                #continue was here, to continue while loop, replaced by break
                break
            for attribute in State.metrics_to_predict:
                if(not prediction[attribute].prediction_valid):
                    #continue was here, to continue while loop, replaced by break
                    break
                if (State.disconnected or State.check_stale_connection()):
                    logging.info("Possible problem due to disconnection or a stale connection")
                    #State.connection.connect()
                message_not_sent = True
                current_time = int(time.time())
                prediction_message_body = {
                    "metricValue": float(prediction[attribute].value),
                    "level": 3,
                    "timestamp": current_time,
                    "probability": 0.95,
                    "confidence_interval": [float(prediction[attribute].lower_confidence_interval_value) ,  float(
                        prediction[attribute].upper_confidence_interval_value)],
                    "predictionTime": prediction_time,
                    "refersTo": "todo",
                    "cloud": "todo",
                    "provider": "todo",
                }
                training_models_message_body = {
                    "metrics": State.metrics_to_predict,
                    "forecasting_method": "exponentialsmoothing",
                    "timestamp": current_time,
                }
                while (message_not_sent):
                    try:
                        #for publisher in State.broker_publishers:
                        #    if publisher.
                        for publisher in State.broker_publishers:
                            #if publisher.address=="eu.nebulouscloud.monitoring.preliminary_predicted.exponentialsmoothing"+attribute:

                            if publisher.key=="publisher_"+attribute:
                                publisher.send(prediction_message_body)


                        #State.connection.send_to_topic('intermediate_prediction.%s.%s' % (id, attribute), prediction_message_body)

                        #State.connection.send_to_topic('training_models',training_models_message_body)
                        message_not_sent = False
                        print_with_time("Successfully sent prediction message for %s to topic eu.nebulouscloud.preliminary_predicted.%s.%s\n\n%s\n\n" % (attribute, id, attribute, prediction_message_body))
                    except ConnectionError as exception:
                        #State.connection.disconnect()
                        #State.connection = messaging.morphemic.Connection('admin', 'admin')
                        #State.connection.connect()
                        logging.error("Error sending intermediate prediction"+str(exception))
                        State.disconnected = False

        if (first_prediction is not None):
            State.previous_prediction = first_prediction #first_prediction is the first of the batch of the predictions which are produced. The size of this batch is set by the State.total_time_intervals_to_predict (currently set to 8)

        #State.number_of_days_to_use_data_from = (prediction_horizon - State.prediction_processing_time_safety_margin_seconds) / (wait_time / State.number_of_days_to_use_data_from)
        #State.number_of_days_to_use_data_from = 1 + int(
        #    (prediction_horizon - State.prediction_processing_time_safety_margin_seconds) /
        #    (wait_time / State.number_of_days_to_use_data_from)
        #)


#class Listener(messaging.listener.MorphemicListener):

class Bootstrap(connector.ConnectorHandler):

    start_forecasting = None # Whether the component should start (or keep on) forecasting
    prediction_thread = None

    def ready(self, context):
        if context.has_publisher('state'):
            context.publishers['state'].starting()
            context.publishers['state'].started()
            context.publishers['state'].custom('forecasting')
            context.publishers['state'].stopping()
            context.publishers['state'].stopped()

            context.publishers['publisher_cpu_usage'].send({
                 'hello': 'world'
            })

    def on_message(self, key, address, body, context, **kwargs):
        application_name = "default_application"
        address = address.replace("topic://eu.nebulouscloud.","")
        if (address).startswith(State.MONITORING_DATA_PREFIX):
            address = address.replace(State.MONITORING_DATA_PREFIX+".","",1)

            logging.info("New monitoring data arrived at topic "+address)
            logging.info(body)

        elif (address).startswith(State.FORECASTING_CONTROL_PREFIX):
            address = address.replace(State.FORECASTING_CONTROL_PREFIX+".","",1)
            logging.info("The address is " + address)

            if address == 'metrics_to_predict':

                State.initial_metric_list_received = True
                print_with_time("Inside message handler for metrics_to predict")
                #body = json.loads(body)
                #for element in body:
                #    State.metrics_to_predict.append(element["metric"])

            elif address == 'test.exponentialsmoothing':
                State.testing_prediction_functionality = True

            elif address == 'start_forecasting.exponentialsmoothing':
                try:
                    State.metrics_to_predict = body["metrics"]
                    print_with_time("Received request to start predicting the following metrics: "+ ",".join(State.metrics_to_predict))
                    State.broker_publishers = []
                    for metric in State.metrics_to_predict:
                        State.broker_publishers.append (PredictionPublisher(metric))
                    State.publishing_connector = connector.EXN('publishing_exsmoothing', handler=Bootstrap(),#consumers=list(State.broker_consumers),
                     consumers=[],
                     publishers=State.broker_publishers,
                     url="localhost",
                     port="5672",
                     username="admin",
                     password="admin"
                     )

                    thread = threading.Thread(target=State.publishing_connector.start,args=())
                    thread.start()

                except Exception as e:
                    print_with_time("Could not load json object to process the start forecasting message \n"+str(body))
                    return

                #if (not State.initial_metric_list_received):
                #    print_with_time("The initial metric list has not been received,
                #therefore no predictions are generated")
                #    return

                try:
                    Bootstrap.start_forecasting = True
                    State.epoch_start = body["epoch_start"]
                    prediction_horizon = int(body["prediction_horizon"])
                    State.next_prediction_time = update_prediction_time(State.epoch_start,prediction_horizon,State.prediction_processing_time_safety_margin_seconds) # State.next_prediction_time was assigned the value of State.epoch_start here, but this re-initializes targeted prediction times after each start_forecasting message, which is not desired necessarily
                    print_with_time("A start_forecasting message has been received, epoch start and prediction horizon are "+str(State.epoch_start)+", and "+str(prediction_horizon)+ " seconds respectively")
                except Exception as e:
                    print_with_time("Problem while retrieving epoch start and/or prediction_horizon")
                    return

                with open(State.configuration_file_location, "r+b") as f:

                    State.configuration_details.load(f, "utf-8")

                    # Do stuff with the p object...
                    initial_seconds_aggregation_value, metadata = State.configuration_details["number_of_seconds_to_aggregate_on"]
                    initial_seconds_aggregation_value = int(initial_seconds_aggregation_value)

                    if (prediction_horizon<initial_seconds_aggregation_value):
                        print_with_time("Changing number_of_seconds_to_aggregate_on to "+str(prediction_horizon)+" from its initial value "+str(initial_seconds_aggregation_value))
                        State.configuration_details["number_of_seconds_to_aggregate_on"] = str(prediction_horizon)

                    f.seek(0)
                    f.truncate(0)
                    State.configuration_details.store(f, encoding="utf-8")


                maximum_time_required_for_prediction = State.prediction_processing_time_safety_margin_seconds #initialization, assuming X seconds processing time to derive a first prediction
                if ((self.prediction_thread is None) or (not self.prediction_thread.is_alive())):
                    self.prediction_thread = threading.Thread(target = calculate_and_publish_predictions, args =[prediction_horizon,maximum_time_required_for_prediction])
                    self.prediction_thread.start()

                #waitfor(first period)

            elif address == 'stop_forecasting.exponentialsmoothing':
                #waitfor(first period)
                print_with_time("Received message to stop predicting some of the metrics")
                metrics_to_remove = json.loads(body)["metrics"]
                for metric in metrics_to_remove:
                    if (State.metrics_to_predict.__contains__(metric)):
                        print_with_time("Stopping generating predictions for metric "+metric)
                        State.metrics_to_predict.remove(metric)
                if len(State.metrics_to_predict)==0:
                    Bootstrap.start_forecasting = False
                    self.prediction_thread.join()

            else:
                print_with_time("The address was "+ address +" and did not match metrics_to_predict/test.exponentialsmoothing/start_forecasting.exponentialsmoothing/stop_forecasting.exponentialsmoothing")
                #        logging.info(f"Received {key} => {address}")
        else:
            print_with_time("Received message "+body+" but could not handle it")
def get_dataset_file(attribute):
    pass


if __name__ == "__main__":
    os.chdir("exponential-smoothing-predictor/src/r_predictors")
    State.configuration_file_location = sys.argv[1]
    Utilities.load_configuration()
# Subscribe to retrieve the metrics which should be used


    id = "exponentialsmoothing"
    State.disconnected = True

    #while(True):
    #    State.connection = messaging.morphemic.Connection('admin', 'admin')
    #    State.connection.connect()
    #    State.connection.set_listener(id, Listener())
    #    State.connection.topic("test","helloid")
    #    State.connection.send_to_topic("test","HELLO!!!")
    #exit(100)

    while True:
        topics_to_subscribe = ["eu.nebulouscloud.monitoring.metric_list","eu.nebulouscloud.monitoring.realtime.>","eu.nebulouscloud.forecasting.start_forecasting.exponentialsmoothing","eu.nebulouscloud.forecasting.stop_forecasting.exponentialsmoothing"]
        current_consumers = []

        for topic in topics_to_subscribe:
            current_consumer = core.consumer.Consumer('monitoring_'+topic, topic, topic=True,fqdn=True)
            State.broker_consumers.append(current_consumer)
            current_consumers.append(current_consumer)
        State.subscribing_connector = connector.EXN('slovid', handler=Bootstrap(),
                                                    #consumers=list(State.broker_consumers),
                                                    consumers=State.broker_consumers,
                                                    url="localhost",
                                                    port="5672",
                                                    username="admin",
                                                    password="admin"
                                                    )


        #connector.start()
        thread = threading.Thread(target=State.subscribing_connector.start,args=())
        thread.start()
        State.disconnected = False;

        print_with_time("Checking (EMS) broker connectivity state, possibly ready to start")
        if (State.disconnected or State.check_stale_connection()):
            try:
                #State.connection.disconnect() #required to avoid the already connected exception
                #State.connection.connect()
                State.disconnected = True
                print_with_time("Possible problem in the connection")
            except Exception as e:
                print_with_time("Encountered exception while trying to connect to broker")
                print(traceback.format_exc())
                State.disconnected = True
                time.sleep(5)
                continue
        State.disconnection_handler.acquire()
        State.disconnection_handler.wait()
        State.disconnection_handler.release()

    #State.connector.stop()
