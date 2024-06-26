import datetime as dt
import requests
import statistics
from dataclasses import dataclass
from typing import Optional, Dict
from itertools import groupby
from sqlmodel import select
import schedule

from core import log as log_, config
from db.db import service as db_service
from db.models import OpenWeatherData

log = log_.service.logger('open_weather')


@dataclass
class WeatherStatistics:
    span: dt.timedelta
    temperature: float
    wind: float
    clouds: float
    humidity: float
    pressure: float


class OpenWeatherService(config.Component):

    def __init__(self, name):
        super().__init__(name)
        self.apikey = config.ConfigOption(required=True).secret  # type: str
        self.longitude = config.ConfigOption(required=True).float  # type: float
        self.latitude = config.ConfigOption(required=True).float  # type: float
        self.days_of_keeping_data = config.ConfigOption(required=True).integer  # type: int

    def schedule_jobs(self):
        log.debug("scheduling open weather related jobs")
        schedule.every(10).minutes.do(self.get_weather_data)
        schedule.every().day.do(self._clear_data)

    def _clear_data(self):
        db_service.clear_old_data(OpenWeatherData, dt.datetime.now() - dt.timedelta(days=self.days_of_keeping_data))

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

    @staticmethod
    def get_last_data():
        return db_service.get_last(OpenWeatherData)

    def get_weather_data(self):
        weather = self.get_last_data()
        if not weather or weather.timestamp < dt.datetime.now() - dt.timedelta(minutes=5):
            data = self.raw_data
            if data:
                log.info('Retrieved Open weather data')
                weather = OpenWeatherData(
                    temperature=round(data['main']['temp'], 2),
                    wind=data['wind']['speed'],
                    clouds=data['clouds']['all'],
                    pressure=data['main']['pressure'],
                    humidity=data['main']['humidity'],
                    timezone=data['timezone'],
                    sunrise=dt.datetime.fromtimestamp(data['sys']['sunrise']),
                    sunset=dt.datetime.fromtimestamp(data['sys']['sunset']))
                log.info(f"Open weather data: {weather}")
                db_service.add(weather)
        return weather

    @staticmethod
    def get_average_weather(timedelta: dt.timedelta) -> Optional[WeatherStatistics]:
        weathers = db_service.session.exec(select(OpenWeatherData).where(OpenWeatherData.timestamp > dt.datetime.now()-timedelta)).all()
        if weathers:
            average = WeatherStatistics(
                span=timedelta,
                temperature=statistics.mean([w.temperature for w in weathers]),
                wind=statistics.mean([w.wind for w in weathers]),
                clouds=statistics.mean([w.clouds for w in weathers]),
                humidity=statistics.mean([w.humidity for w in weathers]),
                pressure=statistics.mean([w.pressure for w in weathers]))
            log.info(f"Average weather from arduino for the past {timedelta}: {average}")
            return average
        return None

    @staticmethod
    def get_hourly_average_weather_for_last_day() -> Optional[Dict[int, WeatherStatistics]]:
        weathers = db_service.session.exec(select(OpenWeatherData).where(OpenWeatherData.timestamp > dt.datetime.now() - dt.timedelta(hours=24))).all()
        weathers_by_hour = {key: list(value) for key, value in groupby(weathers, key=lambda w: w.timestamp.hour)}
        if len(weathers_by_hour) > 0:
            averages_by_hour = dict()
            log.info('calculating hourly average weather')
            for name, data in weathers_by_hour.items():
                averages_by_hour[name] = WeatherStatistics(
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
