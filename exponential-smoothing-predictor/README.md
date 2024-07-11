# Exponential Smoothing predictor

## Introduction

The exponential smoothing predictor is one of the predictors that will be available to the NebulOuS platform for forecasting. Along with other prediction methods, it provides its input to the Prediction Orchestrator which then aggregates it and forwards finalized predictions.

To be used, it follows the process which is outlined in the NebulOuS wiki page related to the generation of predictions:

https://github.com/eu-nebulous/nebulous/wiki/5.3-Predictions-Generation-Process

The exponential smoothing forecaster is based on the use of the Holt-Winters R library to generate predictions. It uses data stored by the monitoring data persistor module (https://github.com/eu-nebulous/monitoring-data-persistor). Data is resampled in order not to create too much load on the forecasting component. Based on the input events, it generates a number of forward predictions, which can be exploited by the Prediction Orchestrator

## Component outline and use

Before starting the component, please ensure that there is at least one recent prediction (where recent is at most as old as the expected difference between the time of the first prediction and the current time), and at least one data point as old as three times the difference between the first prediction and the current time.
To illustrate, assume that the current time is 1705046000, and the first prediction will happen at 1705046500. Then, one recent datapoint is needed (not older than 1705045500) and at least one older datapoint is needed (not more recent than 1705044500). 
Usually, a couple of minutes of recent data should be enough for predictions a few seconds ahead (please scale accordingly, depending on your scenario)

The component initially waits for a `start_forecasting` sent to the `eu.nebulouscloud.forecasting.start_forecasting.exponentialsmoothing` topic.
An example payload for this event follows:

```json
{
  "name": "_Application1",
    "metrics": ["cpu_usage"],
    "timestamp": 1705046535,
    "epoch_start": 1705046500,
    "number_of_forward_predictions": 5,
    "prediction_horizon": 10
}
```

Once this event is sent, it subscribes to the appropriate metric topics and publishes values as required (in the scenario above, 5 predictions every 10 seconds for the cpu_usage metric).

Optionally, and preferably before the start_forecasting event, the component can receive a metric_list event (Event type 3 in the SLO Severity-based Violation Detector interface). Using the information related to the metrics which is contained there, it will be able to constrain predictions to an admissible range for each metric it provides predictions for.

https://github.com/eu-nebulous/nebulous/wiki/5.2-The-SLO-Severity%E2%80%90based-Violation-Detector-Interface
