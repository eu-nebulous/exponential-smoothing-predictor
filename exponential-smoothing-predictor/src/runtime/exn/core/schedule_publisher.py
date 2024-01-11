import logging

from . import publisher

_logger = logging.getLogger(__name__)


class Publisher(publisher.Publisher):
    send_next = False
    delay = 15

    def __init__(self, delay, key, address, topic=False):
        super(Publisher, self).__init__(key, address, topic)
        self.delay = delay
