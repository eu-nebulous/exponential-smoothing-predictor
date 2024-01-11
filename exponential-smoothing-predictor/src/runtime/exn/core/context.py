from . import link


class Context:

    def __init__(self, connection, base):

        self.connection = connection
        self.base = base
        self.publishers = {}
        self.consumers = {}

    def get_publisher(self, key):
        if key in self.publishers:
            return self.publishers[key]
        return None

    def has_publisher(self, key):
        return key in self.publishers

    def has_consumer(self, key):
        return key in self.consumers

    def register_publisher(self, publisher):
        self.publishers[publisher.key] = publisher

    def register_consumers(self, consumer):
        self.consumers[consumer.key] = consumer

    def build_address_from_link(self, link: link.Link):

        if link.fqdn:
            address = link.address
            if link.topic and not link.address.startswith("topic://"):
                address = f"topic://{address}"
            return address

        address = f"{self.base}.{link.address}"
        if link.topic:
            address = f"topic://{address}"

        return address

    def match_address(self, l: link.Link, event):

        if not event \
                or not event.message \
                or not event.message.address:
            return False

        address = self.build_address_from_link(l)
        return address == event.message.address

    def build_address(self, *actions, topic=False):

        if len(actions) <= 0:
            return self.base

        address = f"{self.base}.{'.'.join(actions)}"
        if topic:
            address = f"topic://{address}"

        return address
