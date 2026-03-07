import datetime as dt
from math import exp
import uuid
import schedule
import json

from scarlet.core import log as log_, config, mqtt_module
import scarlet.services.open_weather as open_weather
import scarlet.services.arduino_weather as arduino_weather
from scarlet.api.schemas import BlindsPydanticSchema, BlindState
from scarlet.db.models import BlindAction
from scarlet.db.db import service as db_service

log = log_.service.logger('blinds')


class BlindsController(config.Controller):
    _scheduled_jobs: list[schedule.Job] = list()
    temperature_limit: float
    light_limit: float
    automation: bool

    def initialize(self):
        mqtt_module.register_subscription("home/blinds/ack", mqtt_module.on_ack)
        log.debug("will subscribe to home/blinds/ack for blinds acknowledgements on connect")

    def schedule_jobs(self):
        log.debug("scheduling blinds related jobs")
        if self.automation:
            schedule.every(10).minutes.do(self.decide_opening_and_closing)
            self._scheduled_jobs.append(schedule.every(10).minutes.do(self.decide_opening_and_closing))

    def check_open_weather_conditions(self) -> bool | None:
        open_weather_data = open_weather.service.get_current_data()
        if not open_weather_data:
            log.error("getting open weather data was not sucessful")
            return None

        log.debug(f"temperature: {open_weather_data.temperature_2m} > {self.temperature_limit}")
        if open_weather_data.temperature_2m < self.temperature_limit:
            log.debug("returning False for open weather conditions")
            return False
        else:
            log.debug("returning True for open weather conditions")
            return True

    def decide_opening_and_closing(self):
        log.info("deciding on opening and closing blinds")
        if self.check_open_weather_conditions():
            arduino_weather_data = arduino_weather.service.get_current_weather()
            if arduino_weather_data:
                if arduino_weather_data.wind < 35:
                    # 1.06 is there to adjust the sensor differences, sqrt is added so the tails are uplifted
                    light_1 = ((arduino_weather_data.light_1) * 1.06 / 4095) ** 0.5
                    light_2 = ((arduino_weather_data.light_2) * 1.00 / 4095) ** 0.5
                    log.debug("adjusted light levels: light_1: %s, light_2: %s, limit: %s", round(light_1, 2), round(light_2, 2), self.light_limit)
                    self.set_blinds(BlindsPydanticSchema(left_blind='down' if light_1 > self.light_limit else 'up', right_blind='down' if light_2 > self.light_limit else 'up'), is_user=False)
                    return
                else:
                    log.info(f"wind speed is too high: {arduino_weather_data.wind} km/h, keeping blinds closed")
            else:
                log.error("no current arduino weather data")

        log.info("all blinds should be closed")
        self.set_blinds(BlindsPydanticSchema(left_blind='up', right_blind='up'), is_user=False)

    def set_blinds(self, item: BlindsPydanticSchema, is_user=False) -> bool:
        log.info(f"setting blinds to {item}")
        message_id = str(uuid.uuid4())
        payload = item.model_dump(mode='json')
        payload["message_id"] = message_id
        mqtt_module.mqtt_client.publish("home/blinds", json.dumps(payload))
        status = mqtt_module.await_ack(message_id)
        db_service.add(BlindAction(
            is_user=is_user,
            blind_name='left_blind',
            position=item.left_blind.value))

        db_service.add(BlindAction(
            is_user=is_user,
            blind_name='right_blind',
            position=item.right_blind.value))
        log.info(f"blinds command acknowledged: {status}")
        return status

    def set_automation(self, state: bool):
        self.automation = state
        if state is False:
            log.debug(f'cancelling {len(self._scheduled_jobs)} scheduled jobs')
            [schedule.cancel_job(j) for j in self._scheduled_jobs]
            self._scheduled_jobs = list()
        else:
            self.schedule_jobs()
        self._self_edit_config(attribute='automation', new_value=state)

    def get_adjustment_curves(self):
        history = arduino_weather.service.get_history(dt.datetime.now() - dt.timedelta(days=1))
        history = [h for h in history if h.timestamp > dt.datetime(dt.date.today().year(), dt.date.today().year(), dt.date.today().year(), 0)]
