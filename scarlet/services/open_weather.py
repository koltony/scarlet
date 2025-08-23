import datetime as dt
import requests
import schedule
import polars as pl
from sqlmodel import select

from scarlet.core import log as log_, config
from scarlet.db.db import service as db_service
from scarlet.db.models import Weather, ForecastedWeather, HistoricalWeather

log = log_.service.logger('open_weather')


class OpenWeatherService(config.Service):
    url: str = "https://api.open-meteo.com/v1/forecast"
    _sunset_time = dt.datetime
    _sunrise_time = dt.datetime

    def schedule_jobs(self):
        log.debug("scheduling open weather related jobs")
        schedule.every().day.at("00:30").do(self._cache_historic_data)
        schedule.every().day.at("00:35").do(self._cache_sun_data)
        schedule.every(2).hours.do(self._cache_forecasted_weather_data)
    
    def initialize(self):
        self._cache_sun_data()

    @property
    def sunrise_time(self):
        return self._sunrise_time

    @property
    def sunset_time(self):
        return self._sunset_time

    def _cache_historic_data(self):
        params = {
            "latitude": 47.71318,
            "longitude": 17.6505,
            "hourly": "temperature_2m,relative_humidity_2m,cloud_cover,precipitation,precipitation_probability,wind_speed_10m,wind_gusts_10m",
            "timezone": "Europe/Berlin",
            "past_days": 5,
            "forecast_days": 0
        }

        try:
            raw_data = requests.get(self.url, params=params, timeout=5)
            df = pl.DataFrame(raw_data.json()['hourly'], schema_overrides={'time': pl.Datetime})
            df = df.rename({'time': 'timestamp'})
            last_historic_datapoint: HistoricalWeather = db_service.get_last(HistoricalWeather)
            df = df.filter(pl.col('timestamp') > last_historic_datapoint.timestamp) if last_historic_datapoint else df
            datapoints = [HistoricalWeather.model_validate(dict_) for dict_ in df.to_dicts()]
            log.info(f'caching historical data: {datapoints}')
            db_service.add_all(datapoints)
        except Exception as e:
            log.error(e)


    def _cache_forecasted_weather_data(self):
        params = {
            "latitude": 47.71318,
            "longitude": 17.6505,
            "hourly": "temperature_2m,relative_humidity_2m,cloud_cover,precipitation,precipitation_probability,wind_speed_10m,wind_gusts_10m",
            "timezone": "Europe/Berlin",
            "past_days": 0,
            "forecast_days": 2
        }
        try:
            raw_data = requests.get(self.url, params=params, timeout=5)
            df = pl.DataFrame(raw_data.json()['hourly'], schema_overrides={'time': pl.Datetime})
            df = df.rename({'time': 'timestamp'})
            db_service.clear_data_after(ForecastedWeather, df.sort('timestamp')['timestamp'][0])
            datapoints = [ForecastedWeather.model_validate(dict_) for dict_ in df.to_dicts()]
            log.info(f'caching forecast data: {datapoints}')
            db_service.add_all(datapoints)
        except Exception as e:
            log.error(e)
    
    def _cache_sun_data(self):
        params = {
            "latitude": 47.71318,
            "longitude": 17.6505,
            "daily": "sunset,sunrise",
            "timezone": "Europe/Berlin",
            "past_days": 0,
            "forecast_days": 1,
        }
        try:
            raw_data = requests.get(self.url, params=params, timeout=5)

            self._sunset_time = dt.datetime.fromisoformat(raw_data.json()['daily']['sunset'][0])
            self._sunrise_time = dt.datetime.fromisoformat(raw_data.json()['daily']['sunrise'][0])            
        except Exception as e:
            log.error(e)

    def get_current_data(self) -> Weather:
        params = {
            "latitude": 47.71318,
            "longitude": 17.6505,
            "current": "temperature_2m,relative_humidity_2m,cloud_cover,precipitation,precipitation_probability,wind_speed_10m,wind_gusts_10m",
            "timezone": "Europe/Berlin",
            "past_days": 0,
            "forecast_days": 0
        }
        try:
            raw_data = requests.get(self.url, params=params, timeout=5)
            df = pl.DataFrame(raw_data.json()['current'], schema_overrides={'time': pl.Datetime})
            df = df.rename({'time': 'timestamp'})
            log.info(f'retreived current weather: {df}')
            return Weather.model_validate(df.to_dicts()[0])
        except Exception as e:
            log.error(f"{e} \n getting current weather from history")
            return db_service.get_last(HistoricalWeather)

    def get_closest_history(self, time: dt.datetime) -> HistoricalWeather:
        return db_service.session.exec(select(HistoricalWeather).where(HistoricalWeather.timestamp < time).order_by(HistoricalWeather.timestamp.desc())).first()

    def get_history(self, time: dt.datetime) -> list[HistoricalWeather]:
        return db_service.session.exec(select(HistoricalWeather).where(HistoricalWeather.timestamp > time)).all()


service = OpenWeatherService('OpenWeatherService')
