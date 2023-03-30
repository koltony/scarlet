import config
import mqtt
from enum import Enum, auto
from dataclasses import dataclass
import datetime as dt
import diskcache
from collections import defaultdict
from typing import Optional, Dict, List
import statistics
import log as log_

log = log_.service.logger('ardu_weather')


class SpanType(Enum):
    day = auto()
    hour = auto()
    minute = auto()


@dataclass
class AverageWeather:
    span: int
    span_type: SpanType
    wind: float
    light: float


@dataclass
class Weather:
    wind: float = 0
    light: float = 0
    rain: bool = False
    time: dt.datetime = dt.datetime.now()


class ArduinoWeather(config.Component):
    def __init__(self, name):
        super().__init__(name)
        self.cache_directory = None  # type: Optional[str]
        self.cache_max_age = None  # type: Optional[int]
        self.cache = None  # type: Optional[diskcache.Cache]
        self.anemometer_milli_volt_out_min = None  # type: Optional[int]
        self.anemometer_milli_volt_out_max = None  # type: Optional[int]
        self.anemometer_max_meter_per_sec = None  # type:Optional[float]
        self.arduino_max_milli_input_voltage = None  # type:Optional[float]
        self.arduino_input_resolution = None  # type: Optional[int]

    def initialize(self):
        with diskcache.Cache(directory=self.cache_directory) as cache:
            self.cache = cache

    def clear_cache(self):
        self.cache.clear()
        log.debug('cache cleared')

    def _cache_data(self, weather: Weather):
        self.clear_old_cache_data()
        self.cache[f'{weather.time}_weather'] = weather
        log.debug(f'weather data is cached: {weather}')

    def clear_old_cache_data(self):
        limit = dt.datetime.now() - dt.timedelta(days=self.cache_max_age)
        log.debug(f'removing weather data before {limit}')
        keys_for_removal = list()
        for name in self.cache.iterkeys():
            weather = self.cache[name]
            if limit > weather.time:
                keys_for_removal.append(name)
        log.debug(f'removed {len(keys_for_removal)} weather data points')
        for x in keys_for_removal:
            del self.cache[x]

    def retrieve_last_from_cache(self) -> Optional[Weather]:
        if len(self.cache) >= 1:
            data = self.cache[self.cache.peekitem(last=True)[0]]
            log.debug(f'retrieved last Arduino Weather datapoint from cache: {data}')
            return data
        else:
            log.warning('No Arduino Weather data found in cache')
            return None

    def _value_to_wind_speed(self, value) -> float:
        """"Converts arduino analog read value to actual wind speed"""
        milli_volt_per_value = self.arduino_input_resolution / self.arduino_max_milli_input_voltage
        delta_voltage = self.anemometer_milli_volt_out_max - self.anemometer_milli_volt_out_min
        meter_per_sec_per_voltage = delta_voltage / self.anemometer_max_meter_per_sec  # mps/mV
        value_voltage = value * milli_volt_per_value
        if value_voltage < self.anemometer_milli_volt_out_min:
            log.debug(f"voltage: {value_voltage} is under threshold: {self.anemometer_milli_volt_out_min} returning 0")
            return 0.0

        meter_per_sec = (value_voltage - self.anemometer_milli_volt_out_min) / meter_per_sec_per_voltage
        km_per_hour = meter_per_sec * 3.6
        log.debug(f"calculated wind speed: {km_per_hour}")
        return round(km_per_hour, 2)

    def get_weather_data(self) -> Optional[Weather]:
        wind = mqtt.service.get_message('wind', clear_message=True)
        light = mqtt.service.get_message('light', clear_message=True)
        rain = mqtt.service.get_message('rain', clear_message=True)
        if wind is not None and light is not None:
            wind = self._value_to_wind_speed(float(wind))
            weather = Weather(wind=wind,
                              light=float(light),
                              rain=bool(rain))
            self._cache_data(weather)
            log.info(f"Got weather data from arduino")
            return weather

        log.debug("Loading arduino weather data from cache")
        weather = self.retrieve_last_from_cache()
        if weather and weather.time > dt.datetime.now() - dt.timedelta(minutes=15):
            return weather
        log.warning("No available weather data from arduino")
        return None

    def get_average_weather(self, minutes: int) -> Optional[AverageWeather]:
        log.debug(f'calculating average weather from {len(self.cache)} datapoints')
        weathers = defaultdict(list)
        if len(self.cache) > 0:
            for name in self.cache.iterkeys():
                weather = self.cache[name]
                minutes = min(minutes, (self.cache_max_age * 60 * 24))
                if weather.time > dt.datetime.now() - dt.timedelta(minutes=minutes):
                    weathers['light'].append(weather.temperature)
                    weathers['wind'].append(weather.temperature)
            if weathers:
                average = AverageWeather(span=minutes,
                                         light=statistics.mean(weathers['light']),
                                         wind=statistics.mean(weathers['wind']))
                log.debug(f"Average weather from arduino for the past {minutes} minutes: {average}")
                return average
            else:
                log.warning(f"No cached arduino weather data in the past  {minutes} minutes to calculate average from")
                return None
        log.warning("No cached  arduino weather data to calculate average from")
        return None

    def get_hourly_average_weather_for_last_day(self) -> Optional[Dict[int, AverageWeather]]:
        if len(self.cache) > 0:
            weathers = defaultdict(list)
            averages = dict()
            log.debug(f'calculating hourly average weather from {len(self.cache)} datapoints')
            for name in self.cache.iterkeys():
                weather = self.cache[name]
                if weather.time > dt.datetime.now() - dt.timedelta(days=1):
                    weathers[weather.time.hour] = weather
            for name, data in weathers.items():
                averages_per_hour = defaultdict(list)
                averages_per_hour['light'].append(data.light)
                averages_per_hour['wind'].append(data.wind)

                averages[name] = AverageWeather(span=1,
                                                span_type=SpanType.hour,
                                                light=statistics.mean(averages_per_hour['light']),
                                                wind=statistics.mean(averages_per_hour['wind']))

            return averages
        log.warning("No data to calculate hourly conditions from")
        return None


service = ArduinoWeather("ArduinoWeatherService")

