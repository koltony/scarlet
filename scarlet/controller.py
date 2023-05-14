import statistics
import time
import schedule
import pandas as pd
from collections import OrderedDict
from typing import Optional, Dict, List
import datetime as dt
import os
import open_weather
import arduino_weather
import google_database
import config
import cache
import http_request
import log as log_

log = log_.service.logger('controller')


class MainController(config.Component):
    def __init__(self, name):
        super().__init__(name=name)
        self.IrrigationController = IrrigationController('IrrigationController')
        self.BlindsController = BlindsController('BlindsController')
        self.DatabaseController = DatabaseController('DatabaseController')
        self.CleanupController = CleanupController('CleanupController')

    def start_process(self):
        self.BlindsController.schedule_jobs()
        self.IrrigationController.schedule_jobs()
        self.DatabaseController.schedule_jobs()
        self.CleanupController.schedule_jobs()
        while True:
            schedule.run_pending()
            time.sleep(0.01)


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


class IrrigationProgram(config.Component):
    def __init__(self, name):
        super().__init__(name=name)
        self.zone1 = config.ConfigOption(required=True).integer  # type: int
        self.zone2 = config.ConfigOption(required=True).integer  # type: int
        self.zone3 = config.ConfigOption(required=True).integer  # type: int
        self.zone_connected = config.ConfigOption(required=True).integer  # type: int
        self.every_x_day = config.ConfigOption(required=True).integer  # type: int


class IrrigationPrograms(config.Component):
    def __init__(self, name):
        super().__init__(name=name)
        self.scores_for_programs = config.ConfigOption(required=True).dictionary  # type: Optional[Dict[str, List[float, float]]]
        self.Program_1 = IrrigationProgram("Program_1")
        self.Program_2 = IrrigationProgram("Program_2")
        self.Program_3 = IrrigationProgram("Program_3")
        self.Program_4 = IrrigationProgram("Program_4")
        self.DefaultProgram = self.Program_2


class IrrigationData(cache.CachedObject):
    def __init__(self, scheduled_time: str, irrigation_program: IrrigationProgram):
        super().__init__()
        self.scheduled_time = scheduled_time
        self.irrigation_program = irrigation_program
        self.is_started = False


class IrrigationController(config.Component):

    def __init__(self, name):
        super().__init__(name=name)
        self.Programs = IrrigationPrograms("Programs")
        self.IrrigationControllerCache = cache.Cache("IrrigationControllerCache")  # type: cache.Cache

    def schedule_jobs(self):
        log.debug("Scheduling Irrigation jobs")
        schedule.every().day.at("04:00").do(self.decide_irrigation)
        schedule.every().minute.do(self.check_irrigation_start)

    def check_irrigation_start(self):
        program = self.IrrigationControllerCache.retrieve_last_from_cache()  # type: Optional[IrrigationData]
        if program and program.is_started is False:
            now = dt.datetime.now()
            log.debug("Checking irrigation start time")
            log.debug(f"Scheduled hour: {program.scheduled_time.split(':')[0]} now: {now.hour} is {int(program.scheduled_time.split(':')[0]) == now.hour} \n"
                      f"Scheduled minute: {program.scheduled_time.split(':')[1]} now: {now.minute} is {int(program.scheduled_time.split(':')[1]) == now.minute}")
            if int(program.scheduled_time.split(':')[0]) == now.hour and int(program.scheduled_time.split(':')[1]) == now.minute:
                log.info("Starting irrigation program")
                program.is_started = True
                self.irrigation_process(program)

    @staticmethod
    def calculate_score() -> Optional[float]:
        log.info("Calculating score for irrigation run")
        df = pd.read_csv(filepath_or_buffer=os.path.join(os.path.dirname(os.path.realpath(__file__)), "resources", "vapour.csv"), header=0, index_col=0)
        open_weather_data = open_weather.service.get_hourly_average_weather_for_last_day()
        scores = list()
        if open_weather_data and not df.empty:
            for name, data in open_weather_data.items():
                temperature = int(data.temperature)
                if temperature < 6:
                    temperature = 6
                if temperature > 35:
                    temperature = 35
                humidity = 5 * round(data.humidity/5)
                VPD = df.at[temperature, str(humidity)]
                scores.append(VPD + (0.03 * data.wind))
            log.debug(f"Calculating average score based on {scores}")
            score = statistics.mean(scores)
            log.debug(f"Calculated score: {score}")
            return score
        log.error("No available score")
        return None

    def get_last_run(self) -> int:
        log.debug("Get last irrigation run")
        today = dt.datetime.now()
        run_dates = OrderedDict({1: False, 2: False, 3: False, 4: False, 5: False, 6: False, 7: False})
        for name in self.IrrigationControllerCache.cache.iterkeys():
            weather = self.IrrigationControllerCache.cache[name]
            time_since = weather.timestamp.day - today.day
            if time_since <= 7:
                run_dates[time_since+1] = True
        log.debug(f"Calculated run timeline: {run_dates}")
        for name, item in run_dates.items():
            if item is True:
                log.debug(f"Irrigation system ran {name} day(s) ago")
                return name
        log.debug(f"Irrigation system ran 7 or more  day(s) ago")
        return 7

    @staticmethod
    def post_irrigation_run(program: IrrigationData):
        data = {'time': dt.datetime.now().strftime("%H:%M:%S"),
                'program_name': program.irrigation_program.name,
                'scheduled_time': program.scheduled_time
                }

        log.info("Posting average weather data to Database")
        google_database.service.set_data(data=data, reference='/irrigation_run')

    def decide_irrigation(self):
        log.info("Making decision on next irrigation run")
        arduino_data = arduino_weather.service.get_weather_data()
#        if arduino_data:
#           if arduino_data.rain == 1:
#                log.info("Its raining outside, turning off irrigation for today")
#                return
        score = self.calculate_score()
        if score is not None:
            for name, program in self.Programs.scores_for_programs.items():
                if program[0] < score < program[1]:
                    p = getattr(self.Programs, name)
                    last_run = self.get_last_run()
                    log.debug(f"(p.every_x_day){p.every_x_day} <= {last_run} (last_run)")
                    if p.every_x_day <= last_run:
                        log.info(f"Using program: {name} in the next run")
                        sunrise = open_weather.service.get_weather_data().sunrise
                        irrigation_data = IrrigationData(f"{sunrise.hour}:{sunrise.minute}", p)
                        self.IrrigationControllerCache.cache_data(irrigation_data)
                        self.post_irrigation_run(IrrigationData(f"{sunrise.hour}:{sunrise.minute}", p))
                        return
                    log.info(f"Program not set because this program should only run every 2nd days, last run: {last_run}")
            log.info("Program not set due to conditions")
        else:
            log.warning("No weather score data available, using default program for next run")
            irrigation_data = IrrigationData(f"6:00", self.Programs.DefaultProgram)
            self.IrrigationControllerCache.cache_data(irrigation_data)
            self.post_irrigation_run(irrigation_data)

    @staticmethod
    def irrigation_process(program: IrrigationData):
        log.info("Starting irrigation")
        http_request.service.send_data(
            '/irrigation',
            {
             'zone1': program.irrigation_program.zone1,
             'zone2': program.irrigation_program.zone2,
             'zone3': program.irrigation_program.zone3,
             'zone_connected': program.irrigation_program.zone_connected,
             'active': 'on'
            }
        )


class BlindsController(config.Component):

    def __init__(self, name):
        super().__init__(name=name)
        self.absolute_wind_speed_limit = config.ConfigOption(required=True).integer  # type: int
        self.wind_speed_limit = config.ConfigOption(required=True).integer  # type: int
        self.light_limit = config.ConfigOption(required=True).integer  # type: int
        self.temperature_limit = config.ConfigOption(required=True).integer  # type: int
        self.first_opening_time = config.ConfigOption(required=True).integer  # type: int

    def schedule_jobs(self):
        log.debug("scheduling blinds related jobs")
        schedule.every(15).minutes.do(self.decide_opening_and_closing)
        schedule.every(35).seconds.do(self.emergency_close_test)

    def emergency_close_test(self):
        log.info("Checking emergency conditions for blinds")
        wind_speed = arduino_weather.service.get_weather_data()
        if wind_speed:
            if wind_speed.wind >= self.absolute_wind_speed_limit:
                log.info(f"wind speed({wind_speed.wind}) is larger than {self.absolute_wind_speed_limit} closing blinds")
                http_request.service.send_data(
                    '/blinds',
                    {'left_blind': 'up', 'right_blind': 'up'})
            return
        wind_speed = open_weather.service.get_weather_data()
        if wind_speed:
            if wind_speed.wind >= self.absolute_wind_speed_limit:
                log.info(f"wind speed({wind_speed.wind}) is larger than {self.absolute_wind_speed_limit} closing blinds")
                http_request.service.send_data(
                    '/blinds',
                    {'left_blind': 'up', 'right_blind': 'up'})
            return

    def check_open_weather_conditions(self, weather: open_weather.Weather) -> bool:
        log.debug(f"Current time: {dt.datetime.now().hour} < {weather.sunset.hour}")
        if dt.datetime.now().hour < weather.sunset.hour:
            log.debug(f"temp: {weather.temperature} > {self.temperature_limit} and wind: {weather.wind} < {self.wind_speed_limit}")
            if weather.wind < self.wind_speed_limit and weather.temperature > self.temperature_limit:
                log.debug(f"returning True for open weather conditions")
                return True
        log.debug(f"returning False for open weather conditions")
        return False

    def check_arduino_weather_conditions(self, weather: arduino_weather.AverageWeather) -> bool:
        log.debug(f"Light levels({weather.light} > {self.light_limit} and wind speed: {weather.wind} < {self.wind_speed_limit}")
        if weather.light > self.light_limit and weather.wind < self.wind_speed_limit:
            log.debug(f"returning True for arduino weather conditions")
            return True
        log.debug(f"returning False for arduino weather conditions")
        return False

    def check_conditions(self) -> Optional[bool]:
        open_weather_data = open_weather.service.get_weather_data()
        arduino_weather.service.get_weather_data()
        if self.first_opening_time < dt.datetime.now().hour < 21:
            arduino_weather_data = arduino_weather.service.get_average_weather(dt.timedelta(minutes=30))
            if open_weather_data and arduino_weather_data:
                log.info("Checking conditions based on arduino and open weather data")
                if self.check_arduino_weather_conditions(arduino_weather_data) and self.check_open_weather_conditions(open_weather_data):
                    return True
                else:
                    return False
            elif open_weather_data:
                log.debug("Only open weather is checked")
                if self.check_open_weather_conditions(open_weather_data):
                    return True
            elif arduino_weather_data:
                log.debug("Only arduino weather is checked")
                if self.check_arduino_weather_conditions(arduino_weather_data):
                    return True
            else:
                log.warning("Issue with Open weather and arduino")
                return None
            return False

    def decide_opening_and_closing(self):
        log.debug("Deciding on opening and closing blinds")
        conditions = self.check_conditions()
        if conditions is True:
            log.info(f"Opening blinds")
            http_request.service.send_data(
                '/blinds',
                {'left_blind': 'down', 'right_blind': 'down'})
        elif conditions is False:
            log.info(f"Closing blinds")
            http_request.service.send_data(
                '/blinds',
                {'left_blind': 'up', 'right_blind': 'up'})


controller = MainController(name='MainController')
