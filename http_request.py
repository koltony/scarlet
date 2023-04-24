import requests
import json
from typing import Optional
import config
import log as log_

log = log_.service.logger('http_request')


class HttpRequest(config.Component):
    def __init__(self, name):
        super().__init__(name)
        self.url = config.ConfigOption(required=True).string

    def get_data(self, topic: str) -> Optional[dict]:
        try:
            response = requests.get(self.url + topic)
            load_data = json.loads(response.text)
        except Exception as e:
            log.error(e)
            return None
        log.debug(f'successfully retrieved data from location: {self.url + topic}')
        return load_data

    def send_data(self, topic: str, data: dict):
        try:
            response = requests.post(self.url + topic, data=json.dumps(data), headers={'Content-type': 'application/json'})
        except Exception as e:
            log.error(e)
        log.debug(f'successfully sent data to location: {self.url + topic}')


service = HttpRequest("HttpRequest")
