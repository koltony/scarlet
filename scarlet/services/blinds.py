import datetime as dt
from math import exp
import schedule

from scarlet.core import log as log_, config
import scarlet.services.open_weather as open_weather
import scarlet.services.arduino_weather as arduino_weather
from scarlet.api.schemas import BlindsPydanticSchema
from scarlet.db.models import BlindAction
from scarlet.db.db import service as db_service

log = log_.service.logger('blinds')


class BlindsController(config.Controller):
    _blinds_status: dict[str, str] = {'left_blind': 'nostate', 'right_blind': 'nostate'}
    _scheduled_jobs: list[schedule.Job] = list()
    temperature_limit: float
    light_limit: float
    cloud_cover_limit: float
    automation: bool

    @property
    def blind_status(self):
        return self._blinds_status

    @blind_status.setter
    def blind_status(self, program: BlindsPydanticSchema):
        self._blinds_status = program.model_dump()

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

    @staticmethod
    def _adjust_light_intensity(light_intensity: float) -> float:
        """"Light intensity during the day change a lot and in the late afternoon shading is still needed but the light intensity is much less"""
        now = dt.datetime.now()
        if not (open_weather.service.sunrise_time < now < open_weather.service.sunset_time):
            log.debug("night time, no need for adjustment")
            return 0

        noon = open_weather.service.sunrise_time + (open_weather.service.sunset_time - open_weather.service.sunrise_time) * 0.5
        center = 0
        spread = 10
        current_time_diff_to_center = min(abs(now.hour + now.minute / 60 - noon.hour + noon.minute / 60), 6)
        return light_intensity / exp(-(current_time_diff_to_center - center) ** 2 / (2 * spread ** 2))

    def check_arduino_weather_conditions(self) -> bool:
        arduino_weather_data = arduino_weather.service.get_current_weather()
        if not arduino_weather_data:
            log.error("no average arduino weather data")
            return False
        adjusted_light = self._adjust_light_intensity(arduino_weather_data.l)
        log.debug(f"light levels({arduino_weather_data.light}adj[{adjusted_light}] > {self.light_limit}")
        if adjusted_light > self.light_limit:
            log.debug("returning True for arduino weather conditions")
            return True
        log.debug("returning False for arduino weather conditions")
        return False

    def decide_opening_and_closing(self):
        log.info("deciding on opening and closing blinds")
        if self.check_open_weather_conditions() and self.check_arduino_weather_conditions():
            log.info("blinds should be open")
            self.blind_status = BlindsPydanticSchema(left_blind='down', right_blind='down')
            db_service.add(BlindAction(is_user=False, is_left_up=False, is_right_up=False))
        else:
            log.info("blinds should be closed")
            self.blind_status = BlindsPydanticSchema(left_blind='up', right_blind='up')
            db_service.add(BlindAction(is_user=False, is_left_up=True, is_right_up=True))

    def set_automation(self, state: bool):
        self.automation = state
        if state is False:
            log.debug(f'cancelling {len(self._scheduled_jobs)} scheduled jobs')
            [schedule.cancel_job(j) for j in self._scheduled_jobs]
            self._scheduled_jobs = list()
        self._self_edit_config(attribute='automation', new_value=state)

