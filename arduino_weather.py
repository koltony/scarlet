import config
import mqtt
from enum import Enum, auto
from dataclasses import dataclass
import datetime as dt
import diskcache
import cache
from collections import defaultdict
from typing import Optional, Dict, List
import statistics
import log as log_

log = log_.service.logger('ardu_weather')


@dataclass
class AverageWeather:
    span: dt.timedelta
    wind: float
    light: float


class Weather(cache.CachedObject):
    def __init__(self, wind: float = 0, light: float = 0, rain: bool = False):
        super().__init__()
        self.wind = wind
        self.light = light
        self.rain = rain

    def __repr__(self):
        return f"Weather(wind={self.wind}, light={self.light}, rain={self.rain})"


class ArduinoWeather(config.Component):
    def __init__(self, name):
        super().__init__(name)
        self.anemometer_milli_volt_out_min = config.ConfigOption(required=True).integer  # type: int
        self.anemometer_milli_volt_out_max = config.ConfigOption(required=True).integer  # type: int
        self.anemometer_max_meter_per_sec = config.ConfigOption(required=True).float  # type: float
        self.arduino_max_milli_input_voltage = config.ConfigOption(required=True).integer  # type: int
        self.arduino_input_resolution = config.ConfigOption(required=True).integer  # type: int
        self.ArduinoWeatherCache = cache.Cache("ArduinoWeatherCache")  # type: cache.Cache

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

    def get_weather_data(self) -> Optional[Weather]:
        wind = mqtt.service.get_message('wind', clear_message=True)
        light = mqtt.service.get_message('light', clear_message=True)
        rain = mqtt.service.get_message('rain', clear_message=True)
        if wind is not None and light is not None:
            wind = self._value_to_wind_speed(float(wind))
            weather = Weather(wind=wind,
                              light=float(light),
                              rain=bool(rain))
            self.ArduinoWeatherCache.cache_data(weather)
            log.info(f"Got weather data from arduino : {weather}")
            return weather

        log.debug("Loading arduino weather data from cache")
        weather = self.ArduinoWeatherCache.retrieve_last_from_cache()
        if weather and weather.timestamp > dt.datetime.now() - dt.timedelta(minutes=15):
            return weather
        log.warning("No available weather data from arduino")
        return None

    def get_average_weather(self, timedelta: dt.timedelta) -> Optional[AverageWeather]:
        log.debug(f'calculating average weather from {len(self.ArduinoWeatherCache.cache)} datapoints')
        weathers = self.ArduinoWeatherCache.retrieve_data_for_period(
            dt.datetime.now() - timedelta) # type: Optional[List[Weather]]
        if weathers:
            average = AverageWeather(
                span=timedelta,
                light=statistics.mean([w.light for w in weathers if w is not None]),
                wind=statistics.mean([w.wind for w in weathers if w is not None]))
            log.info(f"Average weather from arduino for the past {timedelta}")
            return average
        return None

    def get_hourly_average_weather_for_last_day(self) -> Optional[Dict[int, AverageWeather]]:
        if len(self.ArduinoWeatherCache.cache) > 0:
            weathers = self.ArduinoWeatherCache.retrieve_hourly_data_for_day()  # type: Optional[Dict[int, List[Weather]]]
            averages_by_hour = dict()
            if weathers:
                log.info(f'calculating hourly average weather')
                for name, data in weathers.items():
                    averages_by_hour[name] = AverageWeather(
                        span=dt.timedelta(hours=1),
                        light=statistics.mean([w.light for w in data if w is not None]),
                        wind=statistics.mean([w.wind for w in data if w is not None]))
                log.info(f"Averages: {averages_by_hour}")
                return averages_by_hour
            return None


service = ArduinoWeather("ArduinoWeatherService")

