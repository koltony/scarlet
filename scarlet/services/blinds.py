import schedule
from typing import Optional
import datetime as dt
from math import exp

from core import log as log_, config
import services.open_weather as open_weather
import services.arduino_weather as arduino_weather
from api.schemas import BlindsPydanticSchema

log = log_.service.logger('blinds')


class BlindsController(config.Component):

    def __init__(self, name):
        super().__init__(name=name)
        self.light_limit: int = config.ConfigOption(required=True).integer
        self.temperature_limit: int = config.ConfigOption(required=True).integer

        self._blinds_status = {'left_blind': 'nostate', 'right_blind': 'nostate'}

    @property
    def blind_status(self):
        return self._blinds_status

    @blind_status.setter
    def blind_status(self, program: BlindsPydanticSchema):
        self._blinds_status = program.dict()

    def schedule_jobs(self):
        log.debug("scheduling blinds related jobs")
        schedule.every(10).minutes.do(self.decide_opening_and_closing)

    def check_open_weather_conditions(self) -> bool:
        open_weather_data = open_weather.service.get_weather_data()
        log.debug(f"temp: {open_weather_data.temperature} > {self.temperature_limit}")
        if open_weather_data.temperature > self.temperature_limit:
            log.debug("returning True for open weather conditions")
            return True
        else:
            log.debug("returning False for open weather conditions")
            return False

    @staticmethod
    def _adjust_light_intensity(light_intensity: float) -> float:
        """"Light intensity during the day change a lot and in the late afternoon shading is still needed but the light intensity is much less"""
        now = dt.datetime.now()
        open_weather_data = open_weather.service.get_weather_data()
        if not open_weather_data:
            log.error("no open weather data available")
            return 0
        if not (open_weather_data.sunrise < now < open_weather_data.sunset):
            log.debug("night time, no need for adjustment")
            return 0

        noon = open_weather_data.sunrise + (open_weather_data.sunset - open_weather_data.sunrise) * 0.5
        center = 0
        spread = 10
        current_time_diff_to_center = abs(now.hour + now.minute / 60 - noon.hour + noon.minute / 60)
        if current_time_diff_to_center > 6:
            current_time_diff_to_center = 6

        return light_intensity / exp(-(current_time_diff_to_center - center) ** 2 / (2 * spread ** 2))

    def check_arduino_weather_conditions(self) -> bool:
        arduino_weather_data = arduino_weather.service.get_average_weather(dt.timedelta(minutes=30))
        if not arduino_weather_data:
            log.error("no average arduino weather data")
            return False
        adjusted_light = self._adjust_light_intensity(arduino_weather_data.light)
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
        else:
            log.info("blinds should be closed")
            self.blind_status = BlindsPydanticSchema(left_blind='down', right_blind='down')


service = BlindsController("BlindsController")
