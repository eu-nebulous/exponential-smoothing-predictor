from exn import core
from runtime.operational_status.EsPredictorState import EsPredictorState


class PredictionPublisher(core.publisher.Publisher):
    metric_name = ""
    def __init__(self,application_name,metric_name):
        super().__init__('publisher_'+application_name+'-'+metric_name, 'eu.nebulouscloud.preliminary_predicted.'+EsPredictorState.forecaster_name+"."+metric_name, True,True)
        self.metric_name = metric_name

    def send(self, body={}, application=""):
        super(PredictionPublisher, self).send(body, application)
