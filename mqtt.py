import socket

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
        self.username = config.ConfigOption(required=True).secret  # type: str
        self.password = config.ConfigOption(required=True).secret  # type: str
        self.ip_address = config.ConfigOption(required=True).string  # type: str
        self.port = config.ConfigOption(required=True).integer  # type: int
        self.timeout = config.ConfigOption(required=True).integer  # type: int
        self.retry_amounts = config.ConfigOption(required=True).integer  # type: int

        self.client = None

        self.subscriptions = list()  # type: List[str]
        self.packages = dict()  # type: Dict[str, Optional[ Package]]

    def initialize(self):
        self.client = mqtt.Client(self.client_name)
        self.client.username_pw_set(self.username, self.password)
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_connect_fail = self.on_connect_fail
        try:
            log.debug(f"Connecting to {self.ip_address}")
            self.client.connect(host=self.ip_address, port=self.port, keepalive=self.timeout)
            self.client.loop_start()
            time.sleep(2)
        except socket.timeout as e:
            log.error(e)

    @staticmethod
    def on_connect(client, userdata, flags, rc):
        log.info(f'{client} established connection with MQTT server')

    @staticmethod
    def on_disconnect(client, userdata, rc):
        log.info(f'{client} is disconnected from MQTT server')

    @staticmethod
    def on_connect_fail(client, userdata, rc):
        log.error(f'Connection have failed for {client}')

    def on_message(self, client, userdata, msg):
        if msg:
            self.packages[msg.topic] = Package(topic=msg.topic, payload=msg.payload.decode())

    def check_status(self):
        if not self.client.is_connected():
            for i in range(self.retry_amounts):
                log.info(f"{self.client_name} trying to reconnect")
                try:
                    self.client.reconnect()
                except socket.timeout as e:
                    log.error(e.__traceback__)
                if self.client.is_connected:
                    self.client.loop_start()
                    time.sleep(1)
                    self.subscribe(self.subscriptions)
                    break
                else:
                    log.warning(f"{self.retry_amounts + 1 } try to reestablish connection have failed")
                    time.sleep(1)

    def get_message(self, topic: str, clear_message: bool = False) -> Any:
        self.check_status()
        log.debug(f'getting message for topic: {topic}')
        if topic not in self.subscriptions:
            self.subscribe(topics=topic)
        time.sleep(0.2)
        message = self.packages.get(topic)
        if clear_message:
            self.packages[topic] = None
        if message is not None:
            log.debug(f'received {message.payload} for {topic}')
            return message.payload
        else:
            log.debug(f'no message available for {topic}')
            return None

    def subscribe(self, topics: Union[str, List[str]]):
        self.check_status()
        if isinstance(topics, str):
            log.debug(f"Subscribing to: {topics}")
            self.client.subscribe(topics)
            self.subscriptions.append(topics)
        else:
            for topic in topics:
                log.debug(f"Subscribing to: {topics}")
                self.client.subscribe(topic)
                self.subscriptions.append(topic)

    def publish(self, topic: str, payload: Any, retain: bool = False, is_silent=False):
        if topic not in self.subscriptions:
            self.subscribe(topics=topic)
        self.client.publish(topic=topic, payload=payload, retain=retain)
        if not is_silent:
            log.info(f"published message: {payload} for topic: {topic}")


service = MqttService('MqttService')

