from dataclasses import dataclass
import datetime as dt
from typing import Optional, Dict
import statistics
from itertools import groupby

from scarlet.core import log as log_, config
from scarlet.api.schemas import ArduinoWeatherPydanticSchema
from scarlet.db.models import ArduinoWeatherModel
from scarlet.db.db import service as db_service

log = log_.service.logger('ardu_weather')


@dataclass
class WeatherStatistics:
    span: dt.timedelta
    wind: float
    light: int


class ArduinoWeather(config.Component):
    def __init__(self, name):
        super().__init__(name)
        self.anemometer_milli_volt_out_min = config.ConfigOption(required=True).integer  # type: int
        self.anemometer_milli_volt_out_max = config.ConfigOption(required=True).integer  # type: int
        self.anemometer_max_meter_per_sec = config.ConfigOption(required=True).float  # type: float
        self.arduino_max_milli_input_voltage = config.ConfigOption(required=True).integer  # type: int
        self.arduino_input_resolution = config.ConfigOption(required=True).integer  # type: int

    def _value_to_wind_speed(self, value) -> float:
        """"Converts arduino analog read value to actual wind speed"""
        milli_volt_per_value = self.arduino_input_resolution / self.arduino_max_milli_input_voltage
        delta_voltage = self.anemometer_milli_volt_out_max - self.anemometer_milli_volt_out_min
        meter_per_sec_per_voltage = delta_voltage / self.anemometer_max_meter_per_sec  # mps/mV
        value_voltage = value * milli_volt_per_value
        log.debug(f"wind sensor voltage: {value_voltage} mV")
        if value_voltage < self.anemometer_milli_volt_out_min:
            log.debug(f"voltage: {value_voltage} is under threshold: {self.anemometer_milli_volt_out_min} returning 0")
            return 0.0

        meter_per_sec = (value_voltage - self.anemometer_milli_volt_out_min) / meter_per_sec_per_voltage
        km_per_hour = round(meter_per_sec * 3.6, 1)
        log.debug(f"calculated wind speed: {km_per_hour}")
        return km_per_hour

    @staticmethod
    def _validate_wind_speed(wind: float) -> bool:
        if wind < 20:
            return True
        historical_data = db_service.session.query(ArduinoWeatherModel).filter(ArduinoWeatherModel.timestamp > dt.datetime.now()-dt.timedelta(hours=1))
        if historical_data:
            max_wind = 0
            for data in historical_data:
                if data.wind > max_wind:
                    max_wind = data.wind
            if max_wind * 2 > wind:
                return True
        log.warning(f"Wind speed of: {wind} km/hour is invalid")
        return False

    def save_weather_data(self, weather: ArduinoWeatherPydanticSchema):
        weather.wind = self._value_to_wind_speed(weather.wind)
        if self._validate_wind_speed(weather.wind):
            log.info(f"Got weather data from arduino : {weather}")
            db_service.add(weather, ArduinoWeatherModel)
            return weather

    @staticmethod
    def get_weather_data():
        return db_service.get_last(ArduinoWeatherModel)

    @staticmethod
    def get_average_weather(timedelta: dt.timedelta) -> Optional[WeatherStatistics]:
        weathers = db_service.session.query(ArduinoWeatherModel).filter(ArduinoWeatherModel.timestamp > dt.datetime.now()-timedelta).all()
        if weathers:
            average = WeatherStatistics(
                span=timedelta,
                light=statistics.mean([w.light for w in weathers if w is not None]),
                wind=statistics.mean([w.wind for w in weathers if w is not None]))
            log.info(f"Average weather from arduino for the past {timedelta} is: {average}")
            return average
        return None

    @staticmethod
    def get_hourly_average_weather_for_last_day() -> Optional[Dict[int, WeatherStatistics]]:
        weathers = db_service.session.query(ArduinoWeatherModel).filter(ArduinoWeatherModel.timestamp > dt.datetime.now() - dt.timedelta(hours=24)).all()
        weathers_by_hour = {key: list(value) for key, value in groupby(weathers, key=lambda w: w.timestamp.hour)}
        if len(weathers_by_hour) > 0:
            averages_by_hour = dict()
            log.info(f'calculating hourly average weather')
            for name, data in weathers_by_hour.items():
                averages_by_hour[name] = WeatherStatistics(
                    span=dt.timedelta(hours=1),
                    light=statistics.mean([w.light for w in data if w is not None]),
                    wind=statistics.mean([w.wind for w in data if w is not None]))
            log.info(f"Averages: {averages_by_hour}")
            return averages_by_hour
        return None


service = ArduinoWeather("ArduinoWeatherService")
