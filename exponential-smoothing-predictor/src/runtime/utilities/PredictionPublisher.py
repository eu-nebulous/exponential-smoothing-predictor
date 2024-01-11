from runtime.exn import core


class PredictionPublisher(core.publisher.Publisher):
    metric_name = ""
    def __init__(self,metric_name):
        super().__init__('publisher_'+metric_name, 'eu.nebulouscloud.preliminary_predicted.'+metric_name, True,True)
        self.metric_name = metric_name

    def send(self, body={}):
        super(PredictionPublisher, self).send(body)
