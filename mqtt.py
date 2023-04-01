import paho.mqtt.client as mqtt
import sys
import time
from typing import Any, List, Union, Dict, Optional
from dataclasses import dataclass
import config
import log as log_

log = log_.service.logger('mttq')


class Package:
    def __init__(self, topic, payload):
        self.topic = topic
        self.payload = payload

    def __repr__(self):
        return f'{self.topic}: {self.payload}'


class MqttService(config.Component):

    def __init__(self, name):
        super().__init__(name)
        self.client_name = config.ConfigOption(required=True).string  # type: str
        self.username = config.ConfigOption(required=True).string  # type: str
        self.password = config.ConfigOption(required=True).string  # type: str
        self.ip_address = config.ConfigOption(required=True).string  # type: str
        self.port = config.ConfigOption(required=True).integer  # type: int
        self.timeout = config.ConfigOption(required=True).integer  # type: int
        self.retry_amounts = config.ConfigOption(required=True).integer  # type: int

        self.client = None
        self.is_connected = False

        self.subscriptions = list()  # type: List[str]
        self.packages = dict()  # type: Dict[str, Optional[ Package]]

    def connection(self):
        if not self.is_connected:
            self.client.connect(self.ip_address, self.port, keepalive=self.timeout)
            self.client.loop_start()

    def initialize(self):
        self.client = mqtt.Client(self.client_name)
        self.client.username_pw_set(self.username, self.password)
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_connect_fail = self.on_connect_fail
        self.test_connection()

    def test_connection(self):
        time.sleep(1)
        log.info("Starting MainController test")
        for i in range(self.retry_amounts):
            log.info(f"Test round {i + 1}")
            try:
                self.publish(topic='test', payload='mqtt tester message')
                time.sleep(1)
                if self.get_message(topic='test', clear_message=True) is not None:
                    log.info("mqtt test passed")
                    break
            except Exception as e:
                log.warning(f"{i + 1} test have failed with error")
            log.warning(f"{i + 1} test have failed with response issue")

    def on_connect(self, client, userdata, flags, rc):
        log.info('Connection established with MQTT server')
        self.is_connected = True

    def on_disconnect(self, client, userdata, rc):
        self.subscriptions = list()
        log.info('Disconnected from MQTT server')
        self.client.loop_stop()
        self.is_connected = False

    def on_connect_fail(self, client, userdata, rc):
        self.subscriptions = list()
        log.error('Connection have failed')

    def on_message(self, client, userdata, msg):
        if msg:
            self.packages[msg.topic] = Package(topic=msg.topic, payload=msg.payload.decode())

    def get_message(self, topic: str, clear_message: bool = False) -> Any:
        self.connection()
        log.debug(f'getting message for topic: {topic}')
        self.subscribe(topic)
        time.sleep(0.2)
        message = self.packages.get(topic)
        if clear_message:
            self.packages[topic] = None
        if message is not None:
            log.info(f'received {message.payload} for {topic}')
            return message.payload
        else:
            log.info(f'no message available for {topic}')
            return None

    def subscribe(self, topics: Union[str, List[str]]):
        self.connection()
        if isinstance(topics, str):
            if topics not in self.subscriptions:
                log.debug(f"Subscribing to: {topics}")
                self.client.subscribe(topics)
        else:
            for topic in topics:
                if topics not in self.subscriptions:
                    log.debug(f"Subscribing to: {topics}")
                    self.client.subscribe(topic)

    def publish(self, topic: str, payload: Any, retain: bool = False, is_silent=False):
        self.subscribe(topics=topic)
        self.client.publish(topic=topic, payload=payload, retain=retain)
        if not is_silent:
            log.info(f"published message: {payload} for topic: {topic}")

    def keep_connection_alive(self):
        self.publish(topic="keep_alive", payload="alive", is_silent=True)


service = MqttService('MqttService')

