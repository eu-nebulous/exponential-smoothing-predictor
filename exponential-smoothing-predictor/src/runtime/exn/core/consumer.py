import datetime

from proton import Message, Event
from . import link
import logging

_logger = logging.getLogger(__name__)


class Consumer(link.Link):

    def on_message(self, body, **kwargs):
        _logger.debug(f"{self.address} Got {body} ")

    def should_handle(self, event: Event):
        if event.link == self._link:
            return True
