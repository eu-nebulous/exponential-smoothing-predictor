from exn import core
from runtime.operational_status.EsPredictorState import EsPredictorState


class PredictionPublisher(core.publisher.Publisher):
    metric_name = ""
    private_publisher = None
    def __init__(self,application_name,metric_name):
        super().__init__('publisher_'+application_name+'-'+metric_name, EsPredictorState.get_prediction_publishing_topic(metric_name), True,True)
        self.metric_name = metric_name
        self.private_publisher = self

    def send(self, body={}, application_name=""):
        try:
            super(PredictionPublisher, self).send(body, application_name)

        except Exception as e:
            self.private_publisher = super().__init__('publisher_'+application_name+'-'+self.metric_name, EsPredictorState.get_prediction_publishing_topic(self.metric_name), True,True)
            super(PredictionPublisher, self).send(body, application_name)
