import logging
import os

from dotenv import load_dotenv
from proton.handlers import MessagingHandler
from proton.reactor import Container

from .core import context as core_context, state_publisher, schedule_publisher
from .settings import base

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)

class ConnectorHandler:
    def __init__(self):
        self.initialized = False


    def set_ready(self,ready, ctx:core_context.Context):
        self.initialized = ready
        self.ready(ctx)

    def ready(self, ctx:core_context.Context):
        pass

    def on_message(self, key, address, body, context, **kwargs):
        pass


class CoreHandler(MessagingHandler):

    def __init__(self,
                 context,
                 handler: ConnectorHandler,
                 publishers = [],
                 consumers = [],
                 ):
        super(CoreHandler, self).__init__()
        self.context=context
        self.publishers=publishers
        self.consumers=consumers
        self.handler = handler
        self.conn = None

    def on_start(self, event) -> None:

        self.conn = event.container.connect(self.context.connection)
        for publisher in self.publishers:
            _logger.info(f"{publisher.address} registering sender")
            address = self.context.build_address_from_link(publisher)
            publisher.set(event.container.create_sender(self.conn,address))
            self.context.register_publisher(publisher)
            _logger.debug(f"{self.context.base} Registering timer { hasattr(publisher, 'delay')}")
            if hasattr(publisher, "delay"):
                _logger.debug(f"{self.context.base} Registering timer")
                event.reactor.schedule(publisher.delay, self)

        for consumer in self.consumers:
            address = self.context.build_address_from_link(consumer)
            _logger.info(f"{self.context.base} Registering consumer {address}")
            consumer.set(event.container.create_receiver(self.conn, address))
            self.context.register_consumers(consumer)

    def on_sendable(self, event):
        if not self.handler.initialized:
            self.handler.set_ready(True, self.context)

    def on_timer_task(self, event):
        _logger.debug(f"{self.context.base} On timer")
        for publisher in self._delay_publishers():
            publisher.send()
            event.reactor.schedule(publisher.delay, self)

    def on_message(self, event):
        try:
            for consumer in self.consumers:
                if consumer.should_handle(event):
                    _logger.debug(f"Received message: {event.message.address}")
                    self.handler.on_message(consumer.key, event.message.address, event.message.body, self.context, event=event)
        except Exception as e:
            _logger.error(f"Received message: {e}")


    def close(self):
        if self.conn:
            self.conn.close()
        else:
            _logger.warning(f"{self.context.base} No open connection")

    def _delay_publishers(self):
        return [p for p in self.publishers if hasattr(p,'delay')]


class EXN:
    def __init__(self, component=None,
                 handler:ConnectorHandler = None,
                 publishers=[],
                 consumers=[],
                **kwargs):

        # Load .env file
        load_dotenv()

        # Validate and set connector
        if not component:
            _logger.error("Component cannot be empty or None")
            raise ValueError("Component cannot be empty or None")
        self.component = component
        self.handler = handler

        self.url = kwargs.get('url',os.getenv('NEBULOUS_BROKER_URL'))
        self.port = kwargs.get('port', os.getenv('NEBULOUS_BROKER_PORT'))
        self.username = kwargs.get('username',os.getenv('NEBULOUS_BROKER_USERNAME'))
        self.password = kwargs.get('password', os.getenv('NEBULOUS_BROKER_PASSWORD'))

        # Validate attributes
        if not self.url:
            _logger.error("URL cannot be empty or None")
            raise ValueError("URL cannot be empty or None")
        if not self.port:
            _logger.error("PORT cannot be empty or None")
            raise ValueError("PORT cannot be empty or None")
        if not self.username:
            _logger.error("USERNAME cannot be empty or None")
            raise ValueError("USERNAME cannot be empty or None")
        if not self.password:
            _logger.error("PASSWORD cannot be empty or None")
            raise ValueError("PASSWORD cannot be empty or None")

        ctx = core_context.Context(
            connection=f"{self.url}:{self.port}",
            base=f"{base.NEBULOUS_BASE_NAME}.{self.component}",
        )

        if kwargs.get("enable_state",False):
            publishers.append(state_publisher.Publisher())

        if kwargs.get("enable_health",False):
            publishers.append(schedule_publisher.Publisher(
                base.NEBULOUS_DEFAULT_HEALTH_CHECK_TIMEOUT,
                'health',
                'health',
                True))

        core_handler = CoreHandler(
            ctx,
            handler,
            publishers,
            consumers
        )

        self.container = Container(core_handler)

    def start(self):
        self.container.run()
