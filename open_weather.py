import datetime as dt
import requests
import config
import diskcache
from enum import Enum, auto
from dataclasses import dataclass
from collections import defaultdict
from typing import Optional, Dict, Any
import log as log_
import statistics

log = log_.service.logger('open_weather')


class SpanType(Enum):
    day = auto()
    hour = auto()
    minute = auto()


@dataclass
class AverageWeather:
    span: int
    span_type: SpanType
    temperature: float
    wind: float
    clouds: float
    humidity: float
    pressure: float


@dataclass
class Weather:
    temperature: float
    wind: float
    clouds: float
    pressure: float
    humidity: float
    timezone: int
    sunrise: dt.datetime
    sunset: dt.datetime
    time: dt.datetime = dt.datetime.now()


class OpenWeatherService(config.Component):

    def __init__(self, name):
        super().__init__(name)
        self.apikey = None  # type: Optional[str]
        self.longitude = None  # type: Optional[float]
        self.latitude = None  # type: Optional[float]
        self.cache_directory = None  # type: Optional[str]
        self.cache_max_age = None  # type: Optional[int]
        self.cache = None  # type: Optional[diskcache.Cache]

    def initialize(self):
        with diskcache.Cache(directory=self.cache_directory) as cache:
            self.cache = cache

    @property
    def raw_data(self):
        try:
            raw = requests.get(f'https://api.openweathermap.org/data/2.5/weather?lat={self.latitude}&lon={self.longitude}&appid={self.apikey}&units=metric').json()
            log.info('weather request was successful')
            log.debug(f"raw_data = {raw}")
            return raw
        except Exception as e:
            log.error(f'request failed: {e}')
            return None

    def clear_cache(self):
        self.cache.clear()
        log.debug('cache cleared')

    def _cache_data(self, weather: Weather):
        self.clear_old_cache_data()
        self.cache[f'{weather.time}_weather'] = weather
        log.debug(f'weather data is cached: {weather}')

    def clear_old_cache_data(self):
        limit = dt.datetime.now() - dt.timedelta(days=self.cache_max_age)
        log.info(f'removing weather data before {limit}')
        keys_for_removal = list()
        for name in self.cache.iterkeys():
            weather = self.cache[name]
            if limit > weather.time:
                keys_for_removal.append(name)
        log.debug(f'removed {len(keys_for_removal)} weather data points')
        for x in keys_for_removal:
            del self.cache[x]

    def retrieve_last_from_cache(self) -> Optional[Weather]:
        data = self.cache[self.cache.peekitem(last=True)[0]]
        if data:
            log.debug(f'retrieved last datapoint from cache: {data}')
            return data
        else:
            log.error('no data found in cache')
            return None

    def get_weather_data(self) -> Optional[Weather]:
        data = self.raw_data
        if data:
            log.info(f'retrieved weather data')
            weather = Weather(temperature=round(data['main']['temp'], 2),
                              wind=data['wind']['speed'],
                              clouds=data['clouds']['all'],
                              pressure=data['main']['pressure'],
                              humidity=data['main']['humidity'],
                              timezone=data['timezone'],
                              time=dt.datetime.fromtimestamp(data['dt']),
                              sunrise=dt.datetime.fromtimestamp(data['sys']['sunrise']),
                              sunset=dt.datetime.fromtimestamp(data['sys']['sunset']))
            log.info(f"Online weather data: {weather}")
            self._cache_data(weather)
        else:
            log.warning('no online weather data trying from cache')
            weather = self.retrieve_last_from_cache()
            if weather is None:
                log.warning('No data in cache')
                return None

        return weather

    def get_average_weather(self, days: int) -> Optional[AverageWeather]:
        weathers = defaultdict(list)
        if len(self.cache) > 0:
            log.debug(f'calculating average weather from {len(self.cache)} datapoints')
            for name in self.cache.iterkeys():
                weather = self.cache[name]
                if weather.time > dt.datetime.now() - dt.timedelta(days=min(days, self.cache_max_age)):
                    weathers['temperature'].append(weather.temperature)
                    weathers['clouds'].append(weather.clouds)
                    weathers['wind'].append(weather.wind)
                    weathers['humidity'].append(weather.humidity)
                    weathers['pressure'].append(weather.pressure)
            average = AverageWeather(span=days,
                                     span_type= SpanType.day,
                                     temperature=statistics.mean(weathers['temperature']),
                                     wind=statistics.mean(weathers['wind']),
                                     clouds=statistics.mean(weathers['clouds']),
                                     humidity=statistics.mean(weathers['humidity']),
                                     pressure=statistics.mean(weathers['pressure']))
            log.info(f"Average weather for the past {days} days: {average}")

        else:
            log.warnig('No weather information to calculate average')
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
                averages_per_hour['temperature'].append(data.temperature)
                averages_per_hour['clouds'].append(data.clouds)
                averages_per_hour['wind'].append(data.wind)
                averages_per_hour['humidity'].append(data.humidity)
                averages_per_hour['pressure'].append(data.pressure)

                averages[name] = AverageWeather(span=1,
                                                span_type=SpanType.hour,
                                                temperature=statistics.mean(averages_per_hour['temperature']),
                                                wind=statistics.mean(averages_per_hour['wind']),
                                                clouds=statistics.mean(averages_per_hour['clouds']),
                                                humidity=statistics.mean(averages_per_hour['humidity']),
                                                pressure=statistics.mean(averages_per_hour['pressure']))
            return averages
        log.warning("No data to calculate hourly conditions from")
        return None


service = OpenWeatherService('WeatherService')
