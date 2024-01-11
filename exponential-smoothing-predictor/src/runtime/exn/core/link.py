
from proton import Link as pLink
class Link:

    fqdn=False
    def __init__(self, key, address, topic=False, fqdn=False):

        self.key = key
        self.address = address
        self._link = None
        self.topic= topic
        self.fqdn= fqdn


    def set(self, link:pLink):
        # The proton container creates a sender
        # so we just use composition instead of extension
        self._link = link
