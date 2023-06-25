import schedule
from typing import Optional
import datetime as dt
from math import exp

from scarlet.core import log as log_, config
import scarlet.services.open_weather as open_weather
import scarlet.services.arduino_weather as arduino_weather
from scarlet.api.schemas import BlindsPydanticSchema

log = log_.service.logger('blinds')


class BlindsController(config.Component):

    def __init__(self, name):
        super().__init__(name=name)
        self.absolute_wind_speed_limit = config.ConfigOption(required=True).integer  # type: int
        self.wind_speed_limit = config.ConfigOption(required=True).integer  # type: int
        self.light_limit = config.ConfigOption(required=True).integer  # type: int
        self.temperature_limit = config.ConfigOption(required=True).integer  # type: int
        self.first_opening_time = config.ConfigOption(required=True).integer  # type: int
        self.closing_time = config.ConfigOption(required=True).integer  # type: int
        self._blinds_status = {'left_blind': 'nostate', 'right_blind': 'nostate'}

    def schedule_jobs(self):
        log.debug("scheduling blinds related jobs")
        schedule.every(15).minutes.do(self.decide_opening_and_closing)
        schedule.every(35).seconds.do(self.emergency_close_test)

    def emergency_close_test(self):
        log.info("Checking emergency conditions for blinds")
        wind_speed = arduino_weather.service.get_weather_data()
        if wind_speed and wind_speed.wind >= self.absolute_wind_speed_limit - 5:
            log.info(f"wind speed({wind_speed.wind}) is larger than {self.absolute_wind_speed_limit-5} closing blinds")
            self._blinds_status = {'left_blind': 'up', 'right_blind': 'up'}
            return
        wind_speed = open_weather.service.get_weather_data()
        if wind_speed and wind_speed.wind >= self.absolute_wind_speed_limit:
            log.info(f"wind speed({wind_speed.wind}) is larger than {self.absolute_wind_speed_limit} closing blinds")
            self._blinds_status = {'left_blind': 'up', 'right_blind': 'up'}

    def check_open_weather_conditions(self, weather) -> bool:
        log.debug(f"Current time: {dt.datetime.now().hour} < {weather.sunset.hour}")
        if dt.datetime.now().hour < weather.sunset.hour:
            log.debug(f"temp: {weather.temperature} > {self.temperature_limit} and wind: {weather.wind+5} < {self.wind_speed_limit}")
            if weather.wind < (self.wind_speed_limit+5) and weather.temperature > self.temperature_limit:
                log.debug("returning True for open weather conditions")
                return True
        log.debug("returning False for open weather conditions")
        return False

    @staticmethod
    def _adjust_light_intensity(light_intensity: float) -> float:
        """"Light intensity during the day change a lot and in the late afternoon shading is still needed but the light intensity is much less"""
        now = dt.datetime.now()
        noon = now.replace(hour=12, minute=0)
        center = 0
        spread = 10
        diff = abs(now.hour + now.minute / 60 - noon.hour + noon.minute / 60)
        if diff > 6:
            diff = 6

        return light_intensity / exp(-(diff - center) ** 2 / (2 * spread ** 2))

    def check_arduino_weather_conditions(self, weather: arduino_weather.WeatherStatistics) -> bool:
        adjusted_light = self._adjust_light_intensity(weather.light)
        log.debug(f"Light levels({weather.light}adj[{adjusted_light}] > {self.light_limit} and wind speed: {weather.wind} < {self.wind_speed_limit}")
        if adjusted_light > self.light_limit and weather.wind < self.wind_speed_limit:
            log.debug("returning True for arduino weather conditions")
            return True
        log.debug("returning False for arduino weather conditions")
        return False

    def check_conditions(self) -> Optional[bool]:
        log.debug(f"checking base conditions: {self.first_opening_time} <= {dt.datetime.now().hour} < {self.closing_time} ")
        if self.first_opening_time <= dt.datetime.now().hour < self.closing_time:
            open_weather_data = open_weather.service.get_weather_data()
            arduino_weather_data = arduino_weather.service.get_average_weather(dt.timedelta(minutes=30))
            if open_weather_data and arduino_weather_data:
                log.info("checking conditions based on arduino and open weather data")
                if self.check_arduino_weather_conditions(arduino_weather_data) and self.check_open_weather_conditions(open_weather_data):
                    return True
                else:
                    return False
            elif open_weather_data:
                log.debug("only open weather is checked")
                if self.check_open_weather_conditions(open_weather_data):
                    return True
            elif arduino_weather_data:
                log.warning("only arduino weather is checked")
                if self.check_arduino_weather_conditions(arduino_weather_data):
                    return True
            else:
                log.warning("issue with Open weather and arduino")
                return None
        log.debug("not in operation times")
        return False

    def decide_opening_and_closing(self):
        log.info("deciding on opening and closing blinds")
        conditions = self.check_conditions()
        if conditions is True:
            log.info("opening blinds")
            self._blinds_status = {'left_blind': 'down', 'right_blind': 'down'}
        elif conditions is False:
            log.info("closing blinds")
            self._blinds_status = {'left_blind': 'up', 'right_blind': 'up'}
        else:
            log.error("could not decide on opening or closing blinds")

    def set_blinds(self, program: BlindsPydanticSchema):
        self._blinds_status = program.dict()

    def get_blinds(self):
        return self._blinds_status


service = BlindsController("BlindsController")
