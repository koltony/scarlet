import datetime as dt
import requests
import config
import cache
import diskcache
from enum import Enum, auto
from dataclasses import dataclass
from collections import defaultdict
from typing import Optional, Dict, List, Any
import log as log_
import statistics

log = log_.service.logger('open_weather')


@dataclass
class AverageWeather:
    span: dt.timedelta
    temperature: float
    wind: float
    clouds: float
    humidity: float
    pressure: float


class Weather(cache.CachedObject):
    def __init__(
        self,
        temperature: float,
        wind: float,
        clouds: float,
        pressure: float,
        humidity: float,
        timezone: int,
        sunrise: dt.datetime,
        sunset: dt.datetime
         ):
        super().__init__()
        self.temperature = temperature
        self.wind = wind
        self.clouds = clouds
        self.pressure = pressure
        self.humidity = humidity
        self.timezone = timezone
        self.sunrise = sunrise
        self.sunset = sunset

    def __repr__(self):
        return f"Weather(temperature={self.temperature}," \
               f" wind={self.wind}," \
               f" clouds={self.clouds}," \
               f" pressure={self.pressure}" \
               f" humidity={self.humidity}" \
               f" timezone={self.timezone}" \
               f" sunrise={self.sunrise}" \
               f" sunset={self.sunset})"


class OpenWeatherService(config.Component):

    def __init__(self, name):
        super().__init__(name)
        self.apikey = config.ConfigOption(required=True).secret  # type: str
        self.longitude = config.ConfigOption(required=True).float  # type: float
        self.latitude = config.ConfigOption(required=True).float  # type: float
        self.OpenWeatherCache = cache.Cache("OpenWeatherCache")  # type: cache.Cache

    @property
    def raw_data(self):
        try:
            raw = requests.get(
                f'https://api.openweathermap.org/data/2.5/weather?lat={self.latitude}&lon={self.longitude}&appid={self.apikey}&units=metric').json()
            log.info('weather request was successful')
            log.debug(f"raw_data = {raw}")
            return raw
        except Exception as e:
            log.error(f'request failed: {e}')
            return None

    def get_weather_data(self) -> Optional[Weather]:
        data = self.raw_data
        if data:
            log.info(f'Retrieved Open weather data')
            weather = Weather(temperature=round(data['main']['temp'], 2),
                              wind=data['wind']['speed'],
                              clouds=data['clouds']['all'],
                              pressure=data['main']['pressure'],
                              humidity=data['main']['humidity'],
                              timezone=data['timezone'],
                              sunrise=dt.datetime.fromtimestamp(data['sys']['sunrise']),
                              sunset=dt.datetime.fromtimestamp(data['sys']['sunset']))
            log.info(f"Open weather data: {weather}")
            self.OpenWeatherCache.cache_data(weather)
        else:
            log.warning('no online weather data trying from cache')
            weather = self.OpenWeatherCache.retrieve_last_from_cache()
            if weather is None:
                log.warning('No data in cache')
                return None

        return weather

    def get_average_weather(self, timedelta: dt.timedelta) -> Optional[AverageWeather]:
        log.debug(f'calculating average weather from {len(self.OpenWeatherCache.cache)} datapoints')
        weathers = self.OpenWeatherCache.retrieve_data_for_period(dt.datetime.now() - timedelta)  # type: Optional[List[Weather]]
        if weathers:
            average = AverageWeather(
                span=timedelta,
                temperature=statistics.mean([w.temperature for w in weathers]),
                wind=statistics.mean([w.wind for w in weathers]),
                clouds=statistics.mean([w.clouds for w in weathers]),
                humidity=statistics.mean([w.humidity for w in weathers]),
                pressure=statistics.mean([w.pressure for w in weathers]))
            log.info(f"Average weather from arduino for the past {timedelta}: {average}")
            return average
        return None

    def get_hourly_average_weather_for_last_day(self) -> Optional[Dict[int, AverageWeather]]:
        if len(self.OpenWeatherCache.cache) > 0:
            weathers = self.OpenWeatherCache.retrieve_hourly_data_for_day()  # type: Optional[Dict[int, List[Weather]]]
            averages_by_hour = dict()
            if weathers:
                log.info(f'calculating hourly average weather')
                for name, data in weathers.items():
                    averages_by_hour[name] = AverageWeather(
                        span=dt.timedelta(hours=1),
                        temperature=statistics.mean([w.temperature for w in data if w is not None]),
                        wind=statistics.mean([w.wind for w in data if w is not None]),
                        clouds=statistics.mean([w.clouds for w in data if w is not None]),
                        humidity=statistics.mean([w.humidity for w in data if w is not None]),
                        pressure=statistics.mean([w.pressure for w in data if w is not None]))
                log.info(f"Averages: {averages_by_hour}")
                return averages_by_hour
            return None


service = OpenWeatherService('OpenWeatherService')
