import datetime as dt
import requests
import config
import diskcache
from dataclasses import dataclass
from collections import defaultdict
from typing import Optional, Dict, Any
import log as log_
import statistics

log = log_.service.logger('weather')


@dataclass
class AverageWeather:
    span: int
    temperature: float
    wind: float
    clouds: float

    def __repr__(self):
        return f"AverageWeather(" \
               f" span= {self.span}," \
               f" temperature={self.temperature}," \
               f" wind={self.wind}," \
               f" clouds={self.clouds}," \



@dataclass
class Weather:
    temperature = 20.0
    wind = 0.0
    clouds = 0.0
    time = dt.datetime.now()
    timezone = 3600
    sunrise = None
    sunset = None

    def __repr__(self):
        return f"Weather(" \
               f" temperature={self.temperature}," \
               f" wind={self.wind}," \
               f" clouds={self.clouds}," \
               f" time={self.time}," \
               f" timezone={self.timezone}," \
               f" sunrise={self.sunrise}," \
               f" sunset={self.sunset} )"


class WeatherService(config.Component):

    def __init__(self, name):
        super().__init__(name)
        self.apikey = None
        self.longitude = None
        self.latitude = None
        self.cache_directory = None
        self.cache_max_age = None
        self.cache = None  # type: Optional[diskcache.Cache]

    def initialize(self):
        with diskcache.Cache(directory=self.cache_directory) as cache:
            self.cache = cache

    @property
    def raw_data(self):
        try:
            raw = requests.get(f'https://api.openweathermap.org/data/2.5/weather?lat={self.latitude}&lon={self.longitude}&appid={self.apikey}&units=metric').json()
            log.info('weather request was successful')
            return raw
        except Exception as e:
            log.error(f'request failed: {e}')
            return None

    def clear_cache(self):
        self.cache.clear()
        log.debug('cache cleared')

    def _cache_data(self, weather: Weather):
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

    def get_weather_data(self) -> Weather:
        data = self.raw_data
        if data:
            log.info(f'retrieved weather data')
            weather = Weather()
            weather.temperature = round(data['main']['temp'], 2)
            weather.wind = data['wind']['speed']
            weather.clouds = data['clouds']['all']
            weather.timezone = data['timezone']
            weather.time = dt.datetime.fromtimestamp(data['dt'] + weather.timezone)
            weather.sunrise = dt.datetime.fromtimestamp(data['sys']['sunrise'] + weather.timezone)
            weather.sunset = dt.datetime.fromtimestamp(data['sys']['sunset'] + weather.timezone)
            log.debug(weather)
            self._cache_data(weather)
        else:
            log.warning('no online weather data trying from cache')
            weather = self.retrieve_last_from_cache()
            if weather is None:
                log.warning('No data in cache getting default weather settings')
                return Weather()

        return weather

    def get_average_weather(self, days: int) -> AverageWeather:
        log.debug(f'calculating average weather from {len(self.cache)} datapoints')
        weathers = defaultdict(list)
        if len(self.cache) > 0:
            for name in self.cache.iterkeys():
                weather = self.cache[name]
                if weather.time > dt.datetime.now() - dt.timedelta(days=min(days, self.cache_max_age)):
                    weathers['temperature'].append(weather.temperature)
                    weathers['clouds'].append(weather.temperature)
                    weathers['wind'].append(weather.temperature)
            average = AverageWeather(span=days,
                                     temperature=statistics.mean(weathers['temperature']),
                                     wind=statistics.mean(weathers['wind']),
                                     clouds=statistics.mean(weathers['clouds']))
            log.info(f"Average weather for the past {days} days: {average}")

        else:
            average = AverageWeather(span=days, temperature=20, wind=10, clouds=0)
            log.warnig('No weather information to calculate average, using defaults')
        return average


service = WeatherService('WeatherService')
