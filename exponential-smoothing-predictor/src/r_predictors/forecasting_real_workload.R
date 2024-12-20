#!Rscript

# Copyright (c) 2023 Institute of Communication and Computer Systems
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.        

library(rapportools)
library(gbutils)
library(forecast)
library(ggplot2)
library(properties)
library(xts)
library(anytime)
library(purrr)


# Outline of the operation of the forecasting script
#
# This forecasting script relies on the presence of a dataset which contains the metric values to be forecasted. It is called with three main parameters - dataset path, metric to be forecasted and the time for which the forecast should be produced - and two optional parameters, the alpha and beta coefficients to be used during forecasting. The time for which the forecast should be produced may be ommitted under some circumstances.
#
# To create the final dataset which will be used for predictions, this script creates a timeseries with all times from the beginning of the observations in the dataset, until its end, using 1-second intervals (to allow for predictions based on epoch). In order for the exponential smoothing forecaster to operate satisfactorily, it is necessary to set the `number_of_seconds_to_aggregate_on` variable to a value which is large enough to smooth small fluctuations, yet small enough to allow for reasonable reaction times (e.g 300 seconds). Beware, this number_of_seconds_to_aggregate_on variable is changed (probably increased) at runtime from its initial configuration so that the forecaster does not consume too much time trying to create predictions. This means that more observations will be necessary to guarantee accurate predictions
# Once the creation of the dataset is over, the `configuration_forecasting_horizon` configuration property is evaluated. If this value is positive, the time for which the forecast should be made should be provided as a command line argument, and this allows the formation of a training dataset and a test dataset. If a non-positive horizon is provided, then the `realtime_mode` configuration property is evaluated. In case that this is false, the prediction time does not need to be provided (it means we simply want to evaluate the predictive functionality based on past data), and the next prediction time will be the time of the last observation in the dataset. If the realtime mode parameter is true, then the prediction time needs to be provided, and the script will try to create a prediction using the maximum value between the next prediction time and the last observation time which is available in the dataset - in this case the next prediction time is needed as well.
#Then, the final data points which will be used for the forecasting are determined, and the forecasting models are created, to produce predictions. The user of the script can opt to try finding the best parameters manually, using the `try_to_optimize_parameters` configuration parameter.

find_smape <- function(actual, forecast) {
  return (1/length(actual) * sum(2*abs(forecast-actual) / (abs(actual)+abs(forecast))*100))
}

get_current_epoch_time <- function(){
  return (as.integer(as.POSIXct(Sys.time())))
}

#Assumes an xts time series object as input, with each record having a 1-sec difference from the previous one, and returns the last timestamp which is (or should have been) assigned (if not present).
find_last_timestamp <- function(mydata,next_prediction_time,realtime_mode){
  possible_timestamp <- as.numeric(end(mydata))
  if(realtime_mode){
    #return(min(c(possible_timestamp,next_prediction_time)))
    if (next_prediction_time>possible_timestamp){
      return(possible_timestamp)
    }else{
      print("Possible problem with the requested prediction time, there is already data for a timestamp newer than the time requested to predict for. Returning the newer timestamp, being aware that this will lead to this prediction returning no meaningful output")
      return (possible_timestamp)
    }
  }else{
    return (possible_timestamp)
  }

}

get_time_value <- function(time_object){
  time_object[1][["user.self"]] 
}


####Time the execution of the prediction
start_time  <- proc.time()
time_field_name <- "ems_time" # The field holding the epoch timestamp in the generated csv
time_unit_granularity <- "sec" # Handle monitoring data using this time unit granularity
endpoint_time_unit_granularity <- "seconds"

#configuration_properties <- read.properties(".\\prediction_configuration-windows.properties")
print("Reading properties from the following file:")
print(paste(getwd(),"/prediction_configuration.properties",sep=''))
configuration_properties <- read.properties(paste(getwd(),"/prediction_configuration.properties",sep=''))

realtime_mode <- as.logical(configuration_properties$realtime_mode) #whether or not we should use all datapoints available (True value), or we are only partially using the available dataset (False value) e.g to test the prediction method performance
try_to_optimize_parameters <- as.logical(configuration_properties$try_to_optimize_parameters)
prediction_method <- configuration_properties$prediction_method
number_of_seconds_to_aggregate_on <- as.integer(configuration_properties$number_of_seconds_to_aggregate_on)
preprocessing_required <- FALSE #Required for some/all FCR datasets
write_back_clean_data_file <- FALSE
csv_has_header <- TRUE

periodic_data <- FALSE #Setting to TRUE uses gamma, else gamma is set to FALSE
if (try_to_optimize_parameters){
  frequency_setting <- 12 #12 five-minute intervals per period
}else{ #downsampling to single hours
  frequency_setting <- 1
}

#Parsing of command-line arguments. Providing the alpha and beta values as arguments is entirely optional. Providing the next_prediction_time may be optional or it may be needed, depending on the circumstances. Please refer to the execution flow which is outlined in the beginning of this program

args <- commandArgs(trailingOnly=TRUE)
dataset_to_process <- args[1]
attribute_to_predict <- args[2]
next_prediction_time <- as.numeric(args[3])
alpha_value_argument <- as.double(args[4])
beta_value_argument <- as.double(args[5])

#mydata <- read.csv(configuration_properties$input_data_file, sep=",", header=TRUE)
#mydata <- read.csv(dataset_to_process, sep=",", header=TRUE)

if (file.info(dataset_to_process)$size > 0) {
  # File is not empty, proceed with reading
  data_to_process <- read.csv(dataset_to_process, sep=",", header=TRUE)
} else {
  # File is empty, handle accordingly (e.g., show a message or skip the reading process)
  print(paste("The file ",dataset_to_process," is empty. Please provide a non-empty file."))
  stop()
}
#sanitize data_to_process by removing any very old values which may have been accidentally introduced. For this reason we remove all data points before now - number_of_days*24hrs*3600sec/hr seconds, and we additionally subtract configuration_properties$prediction_processing_time_safety_margin_seconds in order to account for the time it takes to create the dataset and start the prediction process)
current_time <- get_current_epoch_time()
if (!realtime_mode){
  current_time <- tail(data_to_process[time_field_name],1)
}
oldest_acceptable_time_point <- current_time -(as.numeric(configuration_properties$number_of_days_to_use_data_from)*24*3600 + as.numeric(configuration_properties$prediction_processing_time_safety_margin_seconds))
print(paste("Using data after time point",oldest_acceptable_time_point,"..."))
data_to_process <- data_to_process[data_to_process[[time_field_name]]>oldest_acceptable_time_point,]

if (length(data_to_process[,attribute_to_predict])>0){
  print(paste("Constructing fine-grained data series for",attribute_to_predict,"using the requested granularity..."))
}else{
  print("No valid data points remained after enforcing the number_of_days_to_use_data_from configuration option. This may mean that you are trying to predict using realtime mode, using data points older than the number of days specified in the number_of_days_to_use_data_from configuration option")
  stop()
}
#sapply(data_to_process[, time_field_name], is.na)
#anytime(data_to_process[, time_field_name], format = "%Y-%m-%d %H:%M:%OS")

#Fail-safe default
df1 <- xts(as.numeric(data_to_process[,attribute_to_predict]),anytime(data_to_process[,time_field_name]))
date_time_init <- anytime(data_to_process[,time_field_name])
date_time_complete <- seq.POSIXt(
  from=as.POSIXct(min(date_time_init),origin = "1970-01-01"),
  to=as.POSIXct(max(date_time_init),origin = "1970-01-01"),
  by=time_unit_granularity
)
df2 <- merge(df1,xts(,date_time_complete))
mydata <- na.approx(df2)
colnames(mydata)<-c(attribute_to_predict)

print(paste("The complete time series to be predicted for attribute",attribute_to_predict,"has been created"))

configuration_forecasting_horizon <- as.integer(configuration_properties$horizon)
last_timestamp_data <- 0

if (configuration_forecasting_horizon>0){
  print("Using a statically defined horizon from the configuration file")
  forecasting_horizon <- configuration_forecasting_horizon
  last_timestamp_data <- next_prediction_time - forecasting_horizon
  first_timestamp_data <- as.integer(index(mydata[1]))
  #from the number of datapoints, the last 'forecasting_horizon' datapoints will be used for testing
  data_points_number <- next_prediction_time - first_timestamp_data

  mydata <- head(mydata,data_points_number)

  number_of_periods_in_dataset <- length(mydata[,attribute_to_predict])%/%frequency_setting
  #data_points_number<-length(mydata[,attribute_to_predict])
}else {
  last_timestamp_data <- find_last_timestamp(mydata,next_prediction_time,realtime_mode)
  number_of_periods_in_dataset <- length(mydata[,attribute_to_predict])%/%frequency_setting
  data_points_number<-length(mydata[,attribute_to_predict])
  if (!is.na(next_prediction_time)){
    print(paste("Using value",next_prediction_time,"from command line arguments for forecasting horizon, to be derived after subtracting last timestamp which is",last_timestamp_data))
    forecasting_horizon <- next_prediction_time - last_timestamp_data
    if (forecasting_horizon<=0 && realtime_mode){
      print("Cannot proceed with prediction as the horizon should be a positive value")
      stop()
    }
  }else{
    print("Cannot proceed as a proper prediction horizon value could not be determined")
    stop()
  }
}




if (configuration_properties$forecasting_data_slicing_mode == "percentage"){
  forecasting_data_points_limit  <- configuration_properties$forecasting_data_limit *data_points_number
  forecasting_data_points_offset  <- configuration_properties$forecasting_data_offset * data_points_number
  number_of_data_points_used_for_training <- round(as.double(configuration_properties$forecasting_data_used_for_training) * data_points_number)
  number_of_data_points_used_for_testing <- round((1-as.double(configuration_properties$forecasting_data_used_for_training))* data_points_number)
  #data_used_for_training <- 0.95
  #data_used_for_testing <- 1 - data_used_for_training
}else{
  forecasting_data_points_limit <- data_points_number
  forecasting_data_offset <- 0
  # forecasting_data_offset can be from 0 to 1 - beggining to end of dataset

  number_of_data_points_used_for_testing <- base::min(as.numeric(forecasting_horizon),data_points_number%/%2)
  print(paste("Forecasting horizon is",forecasting_horizon))
  number_of_data_points_used_for_training <- data_points_number - number_of_data_points_used_for_testing
  print(paste("Data points number is",data_points_number,"- from these",number_of_data_points_used_for_testing,"will be used for testing. If the horizon is too large, only half of the data points will be used to evaluate the prediction"))
}

#TODO check the code line below for validity - maybe use head and tail
data_points <-tail(head(mydata[,attribute_to_predict],forecasting_data_points_limit),data_points_number-forecasting_data_offset)

###Load time
load_time <- proc.time() - start_time
print(load_time)




if (write_back_clean_data_file){
  write.csv(mydata,configuration_properties$clean_data_file)
  if(!file.exists(configuration_properties$clean_data_file)){
    file.create(configuration_properties$clean_data_file)
  }
}

### Preprocessing time
preprocessing_time<-proc.time() - load_time - start_time

testing_datapoints <- tail(data_points, number_of_data_points_used_for_testing)
if (number_of_seconds_to_aggregate_on<(forecasting_horizon%/%10)) {
  print(paste("Setting new value for number_of_seconds_to_aggregate_on, from ",number_of_seconds_to_aggregate_on," to ",forecasting_horizon%/%10," in order not to make too far-fetched (slow) predictions"))
  number_of_seconds_to_aggregate_on <- forecasting_horizon%/%10
}
mydata.test <- tail(period.apply(testing_datapoints,endpoints(testing_datapoints,endpoint_time_unit_granularity,k=number_of_seconds_to_aggregate_on),mean),forecasting_horizon%/%(number_of_seconds_to_aggregate_on))

if (length(mydata.test)<=0){
  print(paste("Unable to generate predictions as a prediction is requested for a shorter time duration than the aggregation interval (requested prediction with horizon",forecasting_horizon," whereas the aggregation period is",number_of_seconds_to_aggregate_on,")"))
  stop()
}

training_datapoints <- head(data_points, number_of_data_points_used_for_training)
mydata.train <- period.apply(training_datapoints,endpoints(training_datapoints,endpoint_time_unit_granularity,k=number_of_seconds_to_aggregate_on),mean)

#print(paste("length-debugging",length(mydata.train)+1,length(mydata.train)+length(mydata.test)))
mydata_trainseries <- (ts(mydata.train,start=c(1),frequency = frequency_setting))
mydata_testseries <- (ts(mydata.test, start=c(1), frequency = frequency_setting))

if (try_to_optimize_parameters){
  #initialization
  alpha_ticks <- 5
  beta_ticks <- 5
  if (periodic_data){
    gamma_ticks <- 20
  }else{
    gamma_ticks <- -1
  }
  minimum_optimization_variable_value <- 10000000
  optimal_alpha <- 1
  optimal_beta <- 1
  optimal_gamma <- 1

  iterations <- 0
  iteration_average_time <- 0
  last_iteration_time <- proc.time()
  #actual optimization
  for (alpha_counter in seq(1,alpha_ticks)){
    for (beta_counter in seq(-1,beta_ticks)){
      for (gamma_counter in seq(-1,gamma_ticks)){

        alpha_value <- alpha_counter/alpha_ticks
        beta_value <- beta_counter/beta_ticks
        gamma_value <- gamma_counter/gamma_ticks
        if(beta_value<0){
          beta_value <- FALSE
        }
        if(gamma_value<0 || gamma_ticks<0){
          gamma_value <- FALSE
        }

        holt_winters_forecasting_model <- HoltWinters(mydata_trainseries,alpha=alpha_value,beta=beta_value,gamma=gamma_value)

        holt_winters_forecasts <- forecast:::forecast.HoltWinters(holt_winters_forecasting_model, h=forecasting_horizon)

        optimization_variable<-3 #1: Mean error #2 RMSE #3 MAE #4 MPE #5 MAPE #6 MASE #7 ACF1

        optimization_variable_value <- accuracy(holt_winters_forecasts,x=mydata.test,D=0,d=1)[1,optimization_variable]
        # Use [2, optimization_variable] in the above expression to evaluate with the help of the test set and [1, optimization_variable] to evaluate with the help of the training set.
        # Evaluating using the test set can be useful when the quality of multiple step ahead predictions should be measured. On the other hand, evaluating using the training set tries to minimize one-step ahead predictions.
        # Resampling the data can be an alternative to ensure that one-step ahead predictions are performed and therefore the training set can be used to evaluate accuracy.

        #if (gamma_value==FALSE && beta_value==FALSE && alpha_value==0.75){
        #  print(paste(optimization_variable_value,minimum_optimization_variable_value))
        #}
        print(paste("Alpha,beta,gamma: ",alpha_value,beta_value,gamma_value," optimization value",optimization_variable_value," minimum value",minimum_optimization_variable_value))
        if (optimization_variable_value<minimum_optimization_variable_value){

          if (configuration_properties$debug_level>0){
            print(paste("Replacing existing alpha, beta and gamma ",optimal_alpha,",",optimal_beta,",",optimal_gamma,"as",optimization_variable_value,"<",minimum_optimization_variable_value,"with",alpha_value,",",beta_value,",",gamma_value))
          }

          optimal_alpha <- alpha_value
          optimal_beta <- beta_value
          optimal_gamma <- gamma_value
          if (configuration_properties$debug_level>1){
            debug_option <- readline()
            if(debug_option=="beta"){
              print(paste(optimal_beta))
            }
          }
          minimum_optimization_variable_value <- optimization_variable_value

        }

        iterations <- iterations+1
        iteration_average_time <- iteration_average_time + ((proc.time()-last_iteration_time)-iteration_average_time)/iterations
        }
    }
  }
}
#Override of forecasting model with custom values
#optimal_alpha <- 1
#optimal_beta <- FALSE
#optimal_gamma <- FALSE

#Creation of forecasting model
if (try_to_optimize_parameters){
holt_winters_forecasting_model <- HoltWinters(mydata_trainseries,alpha=optimal_alpha,beta=optimal_beta,gamma=optimal_gamma)

ets_forecasting_model <- tryCatch({
ets(mydata_trainseries,alpha = optimal_alpha,beta = optimal_beta,gamma = optimal_gamma) #phi is left to be optimized
}, error = function(e) {
NULL
})



}else{
  if (!is.na(alpha_value_argument) && !is.na(beta_value_argument)){
    if (periodic_data){
      holt_winters_forecasting_model <- HoltWinters(mydata_trainseries,alpha=alpha_value_argument,beta=beta_value_argument)
      ets_forecasting_model <- tryCatch({
        ets(mydata_trainseries,alpha = alpha_value_argument,beta = beta_value_argument)
      }, error = function(e) {
        NULL
      })
    }else{
      holt_winters_forecasting_model <- HoltWinters(mydata_trainseries,alpha=alpha_value_argument,beta=beta_value_argument,gamma=FALSE)
      #ets_forecasting_model <- ets(mydata_trainseries,alpha = alpha_value_argument,beta = beta_value_argument,gamma = FALSE)
      ets_forecasting_model <- tryCatch({
        ets(mydata_trainseries,alpha = alpha_value_argument,beta = beta_value_argument,gamma=FALSE)
      }, error = function(e) {
        NULL
      })
    }
  }else{
    print("No alpha or beta values provided, so will calculate them now")
    if (periodic_data){
      ets_forecasting_model <- ets(mydata_trainseries)
      holt_winters_forecasting_model <- HoltWinters(mydata_trainseries)
    }else{
      ets_forecasting_model <- tryCatch({
          ets(mydata_trainseries,model="ZZN")
        }, error = function(e) {
          NULL
        })
      if (length(mydata_trainseries)<3){
        print("Possible issue expected with a very small trainseries (length is less than 3). The contents of the trainseries are the following:")
        print(mydata_trainseries)
        print("This trainseries originated from the following aggregated data:")
        print(mydata.train)
        print(paste("The number of seconds to aggregate on is:",number_of_seconds_to_aggregate_on))
        print("The above aggregated data was based on these training data points: ")
        print(training_datapoints)
        print("These training data points originate from these data points:")
        print(data_points)
        print(paste("by using the first", number_of_data_points_used_for_training, "data points"))

      }
      holt_winters_forecasting_model <- HoltWinters(mydata_trainseries,gamma=FALSE)
    }
  }
}

print("Starting execution, forecasting horizon, next prediction time and last timestamp data are as follows")
print(paste(forecasting_horizon,next_prediction_time,last_timestamp_data))


if (try_to_optimize_parameters){
  print(paste("The optimal alpha, beta and gamma values are, respectively",optimal_alpha,",",optimal_beta,"and",optimal_gamma))

  if (prediction_method=="Holt-Winters"){
    holt_winters_forecasts <- forecast:::forecast.HoltWinters(holt_winters_forecasting_model, h=forecasting_horizon)
  }
  else if (prediction_method=="ETS"){
    ets_forecasts <- forecast::forecast.ets(ets_forecasting_model, h=forecasting_horizon)
  }

}else{
  if (prediction_method=="Holt-Winters"){
    holt_winters_forecasts <- forecast:::forecast.HoltWinters(holt_winters_forecasting_model, h=forecasting_horizon%/%(number_of_seconds_to_aggregate_on))
  }else{
    ets_forecasts <- forecast::forecast.ets(ets_forecasting_model, h=forecasting_horizon%/%(number_of_seconds_to_aggregate_on))
  }

}


if (prediction_method == "Holt-Winters"){
  holt_winters_accuracy_measures <- accuracy(holt_winters_forecasts,x=mydata.test,D=0,d=1)#d,D values only influence MASE calculation, and are chosen to reflect a non-seasonal time-series
  print(paste("Holt-Winters accuracy measures"))
  print(holt_winters_accuracy_measures)
  print("------------------------------------------------")
}else if (prediction_method == "ETS"){
  ets_accuracy_measures <- accuracy(ets_forecasts,x=mydata.test,D=0,d=1)#d,D values only influence MASE calculation, and are chosen to reflect a non-seasonal time-series
  print("ETS accuracy measures:")
  print(ets_accuracy_measures)
  print("------------------------------------------------")
}
###prediction_time
prediction_time <- proc.time() - preprocessing_time -load_time - start_time
total_time <- proc.time() - start_time

print(paste("The load_time is:",get_time_value(load_time)))
print(paste("The preprocessing time is:",get_time_value(preprocessing_time)))
print(paste("The prediction time is:",get_time_value(prediction_time)))
print(paste("The total time is:",get_time_value(prediction_time)))

if(prediction_method=="ETS"){

  forecast_object <- ets_forecasts

  print(paste("Prediction:",tail(ets_forecasts[["mean"]],n=1)))
  print(paste0("Confidence_interval:",tail((ets_forecasts[["lower"]]),n=1)[2],",",tail((ets_forecasts[["upper"]]),n=1)[2]))
  #2,1: Mean error 2,2: RMSE 2,3 MAE 2,4 MPE 2,5 MAPE 2,6 MASE 2,7 ACF1
  print(paste0("mae:",ets_accuracy_measures[2,3]))
  mse<-as.numeric(ets_accuracy_measures[2,2])*as.numeric(ets_accuracy_measures[2,2])
  print(paste0("mse:",mse)) #square of RMSE
  print(paste0("mape:",ets_accuracy_measures[2,5]))
  print(paste0("smape:",find_smape(ets_forecasts$x,ets_forecasts$fitted)))

}else if (prediction_method=="Holt-Winters"){

  forecast_object <- holt_winters_forecasts

  print(paste0("Prediction:",tail(holt_winters_forecasts[["mean"]],n=1)))
  print(paste0("Confidence_interval:",tail((holt_winters_forecasts[["lower"]]),n=1)[2],",",tail((holt_winters_forecasts[["upper"]]),n=1)[2]))
  print(paste0("mae:",holt_winters_accuracy_measures[2,3]))
  mse<-as.numeric(holt_winters_accuracy_measures[2,2])*as.numeric(holt_winters_accuracy_measures[2,2])
  print(paste0("mse:",mse))
  print(paste0("mape:",holt_winters_accuracy_measures[2,5]))
  print(paste0("smape:",find_smape(holt_winters_forecasts$x,holt_winters_forecasts$fitted)))
}

#GRAPHING DOCUMENTATION

#forecast_object contains the timeseries which is forecasted, the original time series, and the one-step ahead prediction, along with the confidence intervals. When it alone is plotted, with the command forecast_object %>% autoplot(), the black line are the original values of the timeseries, and the single point in the end along with the blue zones, are the intervals which characterize the final prediction is calculated

#To draw the predictions along with the original time series values, we can use the following code:

#x_values <- seq.int(1,length(forecast_object$x)) #This should be changed as needed
#pred_values <- forecast_object$fitted
#observed_values <- forecast_object$x
#residuals <- forecast_object$residuals


#plot(x_values,observed_values,type='l',col="red")
#lines(x_values,residuals,col="blue")
#lines(x_values,pred_values,col="green")

#plot(x=as.numeric(time(forecast_object$x)),forecast_object$x,type='l',col='blue',ylim=c(0,1000))
#lines(x=as.numeric(time(forecast_object$mean)),forecast_object$mean,type='l',col='red')
#65130 was the length of the training dataset
#lines(x=65130+as.numeric(time(mydata_testseries)),mydata_testseries,type='l',col='green')


#dev.off()


if (as.logical(configuration_properties$generate_prediction_png_output)){
  print(paste("creating new figure at",configuration_properties$png_output_file))

  mydata.aggregated <- period.apply(data_points,endpoints(data_points,endpoint_time_unit_granularity,k=number_of_seconds_to_aggregate_on),mean)
  mydata_full_series <- ts(mydata.aggregated,start=c(1),frequency = frequency_setting)

  png(filename=configuration_properties$png_output_file,
      type="cairo",
      units="in",
      width=10,
      height=6,
      pointsize=1,
      res=1200)
    forecast_object %>%
    autoplot() +
    geom_line(
       aes(
         x = as.numeric(time(mydata_full_series)),
         y = as.numeric(mydata_full_series)
         ),
       col = "red",
       size = 0.1
    ) +
   geom_line(
     aes(
       x = as.numeric(time(forecast_object$mean)),
       y = as.numeric(forecast_object$mean)
       #Painting the actual predictions
     ),
     col = "green",
     size = 0.1
   )
  #goes to above line: +
#   geom_line(
#     aes(
#       x = as.numeric(time(forecast_object$mean)),
#       y = as.numeric(forecast_object$mean)
#     ),
#     col = "yellow",
#     size = 0.1
#   )
  dev.off()
}