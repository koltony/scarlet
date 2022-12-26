import datetime as dt
import requests
import diskcache
from dataclasses import dataclass
import cachetools


class Weather:

    def __init__(self):
        self.temperature = 20.0
        self.wind = 0.0
        self.clouds = 0.0
        self.time = None
        self.timezone = 3600
        self.sunrise = None
        self.sunset = None

    @property
    def raw_data(self):
        return requests.get('https://api.openweathermap.org/data/2.5/weather?lat=47.7127&lon=17.6507&appid=df0a162c607b2050fdd840674c5070cf').json()

    def cache_data(self):
        with diskcache.Cache(directory='.../weather', expire=24 * 3600) as cache:
            cache[f'{self.time}_weather'] = {'time': self.time,
                                             'temperature': self.temperature,
                                             'wind': self.wind,
                                             'clouds': self.clouds,
                                             'sunrise': self.sunrise,
                                             'sunset': self.sunset}

    def retrieve_from_cache(self):
        with diskcache.Cache(directory='.../weather', expire=24 * 3600) as cache:
            data = cache[cache.peekitem(last=True)[0]]
        if data:
            self.time = dt.datetime.now()
            self.temperature = data.get('temperature')
            self.wind = data.get('wind')
            self.clouds = data.get('clouds')
            self.sunrise = data.get('sunrise')
            self.sunset = data.get('sunset')

    def refresh_data(self):
        data = self.raw_data
        if data:
            self.temperature = data['main']['temp']
            self.wind = data['wind']['speed']
            self.clouds = data['clouds']['all']
            self.timezone = data['timezone']
            self.time = dt.datetime.fromtimestamp(data['dt'] + self.timezone)
            self.sunrise = dt.datetime.fromtimestamp(data['sys']['sunrise'] + self.timezone)
            self.sunset = dt.datetime.fromtimestamp(data['sys']['sunset'] + self.timezone)
            self.cache_data()
        else:
            self.retrieve_from_cache()


service = Weather()