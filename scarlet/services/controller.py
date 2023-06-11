import schedule
from typing import Optional
import datetime as dt

from scarlet.core import log as log_, config
import scarlet.services.open_weather as open_weather
import scarlet.services.arduino_weather as arduino_weather
from scarlet.db import google_database


log = log_.service.logger('controller')


class MainController(config.Component):
    def __init__(self, name):
        super().__init__(name=name)
        self.DatabaseController = DatabaseController('DatabaseController')
        self.CleanupController = CleanupController('CleanupController')

    def start_process(self):
        self.DatabaseController.schedule_jobs()
        self.CleanupController.schedule_jobs()


class CleanupController(config.Component):
    def __init__(self, name):
        super().__init__(name=name)

    def schedule_jobs(self):
        schedule.every().monday.at("02:00").do(self.delete_logs)
        schedule.every().thursday.at("02:00").do(self.delete_logs)

    @staticmethod
    def delete_logs():
        log.info("flushing logfile")
        log_.service.clear_log_file()


class DatabaseController(config.Component):
    def __init__(self, name):
        super().__init__(name=name)

    @staticmethod
    def initialize():
        google_database.service.listen_to(reference='/settings')

    def schedule_jobs(self):
        schedule.every(15).minutes.do(self.post_average_weather_data)

    @staticmethod
    def post_average_weather_data():
        o_weather = open_weather.service.get_average_weather(timedelta=dt.timedelta(hours=1))
        a_weather = arduino_weather.service.get_average_weather(timedelta=dt.timedelta(minutes=15))
        
        if o_weather and a_weather:
            data = {'time': dt.datetime.now().strftime("%H:%M:%S"),
                    'temperature': o_weather.temperature,
                    'wind': a_weather.wind,
                    'light': a_weather.light}

            log.info("Posting average weather data to Database")
            google_database.service.set_data(data=data, reference='/weather')


controller = MainController(name='MainController')
