import schedule
from typing import Optional
import datetime as dt

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
        self._blinds_status = {'left_blind': 'nostate', 'right_blind': 'nostate'}

    def schedule_jobs(self):
        log.debug("scheduling blinds related jobs")
        schedule.every(15).minutes.do(self.decide_opening_and_closing)
        schedule.every(35).seconds.do(self.emergency_close_test)

    def emergency_close_test(self):
        log.info("Checking emergency conditions for blinds")
        wind_speed = arduino_weather.service.get_weather_data()
        if wind_speed:
            if wind_speed.wind >= self.absolute_wind_speed_limit - 5:
                log.info(f"wind speed({wind_speed.wind}) is larger than {self.absolute_wind_speed_limit-5} closing blinds")
                self._blinds_status = {'left_blind': 'up', 'right_blind': 'up'}
            return
        wind_speed = open_weather.service.get_weather_data()
        if wind_speed:
            if wind_speed.wind >= self.absolute_wind_speed_limit:
                log.info(f"wind speed({wind_speed.wind}) is larger than {self.absolute_wind_speed_limit} closing blinds")
                self._blinds_status = {'left_blind': 'up', 'right_blind': 'up'}
            return

    def check_open_weather_conditions(self, weather) -> bool:
        log.debug(f"Current time: {dt.datetime.now().hour} < {weather.sunset.hour}")
        if dt.datetime.now().hour < weather.sunset.hour:
            log.debug(f"temp: {weather.temperature} > {self.temperature_limit} and wind: {weather.wind+5} < {self.wind_speed_limit}")
            if weather.wind < (self.wind_speed_limit+5) and weather.temperature > self.temperature_limit:
                log.debug(f"returning True for open weather conditions")
                return True
        log.debug(f"returning False for open weather conditions")
        return False

    def check_arduino_weather_conditions(self, weather: arduino_weather.WeatherStatistics) -> bool:
        log.debug(f"Light levels({weather.light} > {self.light_limit} and wind speed: {weather.wind} < {self.wind_speed_limit}")
        if weather.light > self.light_limit and weather.wind < self.wind_speed_limit:
            log.debug(f"returning True for arduino weather conditions")
            return True
        log.debug(f"returning False for arduino weather conditions")
        return False

    def check_conditions(self) -> Optional[bool]:
        open_weather_data = open_weather.service.get_weather_data()
        arduino_weather.service.get_weather_data()
        log.debug(f"checking base conditions: {self.first_opening_time} <= {dt.datetime.now().hour} < 21 ")
        if self.first_opening_time <= dt.datetime.now().hour < 21:
            arduino_weather_data = arduino_weather.service.get_average_weather(dt.timedelta(minutes=30))
            if open_weather_data and arduino_weather_data:
                log.info("checking conditions based on arduino and open weather data")
                if self.check_arduino_weather_conditions(arduino_weather_data) and self.check_open_weather_conditions(open_weather_data):
                    return True
                else:
                    return False
            elif open_weather_data:
                log.debug("Only open weather is checked")
                if self.check_open_weather_conditions(open_weather_data):
                    return True
            elif arduino_weather_data:
                log.warning("Only arduino weather is checked")
                if self.check_arduino_weather_conditions(arduino_weather_data):
                    return True
            else:
                log.warning("Issue with Open weather and arduino")
                return None
        log.debug(f"not in operation times")
        return False

    def decide_opening_and_closing(self):
        log.info("Deciding on opening and closing blinds")
        conditions = self.check_conditions()
        if conditions is True:
            log.info(f"Opening blinds")
            self._blinds_status = {'left_blind': 'down', 'right_blind': 'down'}
        elif conditions is False:
            log.info(f"Closing blinds")
            self._blinds_status = {'left_blind': 'up', 'right_blind': 'up'}
        else:
            log.error(f"Could not decide on opening or closing blinds")

    def set_blinds(self, program: BlindsPydanticSchema):
        self._blinds_status = program.dict()

    def get_blinds(self):
        return self._blinds_status


service = BlindsController("BlindsController")
