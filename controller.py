import statistics

import schedule
import diskcache
import pandas as pd
from collections import OrderedDict
from typing import Optional, Dict, List
import datetime as dt
import open_weather
import arduino_weather
import config
from dataclasses import dataclass
import mqtt
import log as log_

log = log_.service.logger('controller')


class MainController(config.Component):
    def __init__(self, name):
        super().__init__(name=name)
        self.IrrigationController = IrrigationController('IrrigationController')
        self.BlindsController = BlindsController('BlindsController')

    def start_process(self):
        self.BlindsController.schedule_jobs()
        self.IrrigationController.schedule_jobs()


class IrrigationProgram(config.Component):
    def __init__(self, name):
        super().__init__(name=name)
        self.zone1 = None  # type: Optional[int]
        self.zone2 = None  # type: Optional[int]
        self.zone3 = None  # type: Optional[int]
        self.zone_connected = None  # type: Optional[int]
        self.every_x_day = None  # type: Optional[int]


class IrrigationPrograms(config.Component):
    def __init__(self, name):
        super().__init__(name=name)
        self.scores_for_programs = None  # type: Optional[Dict[str, List[float, float]]]
        self.default_program = IrrigationProgram("DefaultProgram")
        self.Program_1 = IrrigationProgram("Program_1")
        self.Program_2 = IrrigationProgram("Program_2")
        self.Program_3 = IrrigationProgram("Program_3")
        self.Program_4 = IrrigationProgram("Program_4")


@dataclass
class IrrigationData:
    time = dt.datetime.now()
    scheduled_time: str
    irrigation_program: IrrigationProgram
    is_started = False


class IrrigationController(config.Component):

    def __init__(self, name):
        super().__init__(name=name)
        self.cache_directory = None  # type: Optional[str]
        self.cache = None  # type: Optional[diskcache.Cache]
        self.cache_max_age = None  # type: Optional[int]
        self.Programs = IrrigationPrograms("Programs")

    def initialize(self):
        with diskcache.Cache(directory=self.cache_directory) as cache:
            self.cache = cache

    def _cache_data(self, data: IrrigationData):
        self.clear_old_cache_data()
        self.cache[f'{data.time}_irrigation_data'] = data
        log.debug(f'weather data is cached: {data}')

    def clear_cache(self):
        self.cache.clear()
        log.debug('cache cleared')

    def clear_old_cache_data(self):
        limit = dt.datetime.now() - dt.timedelta(days=self.cache_max_age)
        log.info(f'removing IrrigationData before {limit}')
        keys_for_removal = list()
        for name in self.cache.iterkeys():
            data = self.cache[name]
            if limit > data.time:
                keys_for_removal.append(name)
        log.debug(f'removed {len(keys_for_removal)} weather data points')
        for x in keys_for_removal:
            del self.cache[x]

    def retrieve_last_from_cache(self) -> Optional[IrrigationData]:
        if len(self.cache) >= 1:
            data = self.cache[self.cache.peekitem(last=True)[0]]
            log.debug(f'Retrieved last IrrigationData from cache')
            return data
        else:
            log.warning('No IrrigationData found in cache')
            return None

    def schedule_jobs(self):
        log.debug("Scheduling Irrigation jobs")
        schedule.every().day.at("04:00").do(self.decide_irrigation)
        schedule.every().minute.do(self.check_irrigation_start)

    def check_irrigation_start(self):
        program = self.retrieve_last_from_cache()
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
        df = pd.read_csv(filepath_or_buffer="resources/vapour.csv", header=0, index_col=0)
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
        for name in self.cache.iterkeys():
            weather = self.cache[name]
            time_since = weather.time.day - today.day
            if time_since <= 7:
                run_dates[time_since+1] = True
        log.debug(f"Calculated run timeline: {run_dates}")
        for name, item in run_dates.items():
            if item is True:
                log.debug(f"Irrigation system ran {name} day(s) ago")
                return name
        log.debug(f"Irrigation system ran 7 or more  day(s) ago")
        return 7

    def decide_irrigation(self):
        log.info("Making decision on next irrigation run")
        self.clear_old_cache_data()
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
                        self._cache_data(IrrigationData(f"{sunrise.hour}:{sunrise.minute}", p))
                        return
                    log.debug("Program not set due to conditions")
        else:
            log.warning("No weather score data available, using default program for next run")
            self._cache_data(IrrigationData(f"6:00", self.Programs.default_program))

    @staticmethod
    def irrigation_process(program: IrrigationData):
        log.info("Starting irrigation")
        mqtt.service.publish('zone1', program.irrigation_program.zone1)
        mqtt.service.publish('zone2', program.irrigation_program.zone2)
        mqtt.service.publish('zone3', program.irrigation_program.zone3)
        mqtt.service.publish('zone_connected', program.irrigation_program.zone_connected)
        mqtt.service.publish('active', 1)


class BlindsController(config.Component):

    def __init__(self, name):
        super().__init__(name=name)
        self.stop_signal_mari = None
        self.open_signal_mari = None
        self.close_signal_mari = None

        self.stop_signal_pisti = None
        self.open_signal_pisti = None
        self.close_signal_pisti = None

        self.absolute_wind_speed_limit = None
        self.wind_speed_limit = None
        self.light_limit = None
        self.temperature_limit = None
        self.first_opening_time = None

    def schedule_jobs(self):
        log.debug("scheduling blinds related jobs")
        schedule.every(15).minutes.do(self.decide_opening_and_closing)
        schedule.every().minute.do(self.emergency_close_test)
        schedule.every(10).minutes.do(self.checkin_to_eclipse_arduino)

    @staticmethod
    def checkin_to_eclipse_arduino():
        return mqtt.service.publish('eclipse_checkin', 'connected')

    def emergency_close_test(self):
        log.debug("Checking emergency conditions for blinds")
        wind_speed = arduino_weather.service.get_weather_data()
        if wind_speed:
            if wind_speed.wind >= self.absolute_wind_speed_limit:
                mqtt.service.publish('mari', self.close_signal_mari)
                mqtt.service.publish('pisti', self.close_signal_pisti)
            return
        wind_speed = open_weather.service.get_weather_data()
        if wind_speed:
            if wind_speed.wind >= self.absolute_wind_speed_limit:
                mqtt.service.publish('mari', self.close_signal_mari)
                mqtt.service.publish('pisti', self.close_signal_pisti)
            return

    def check_open_weather_conditions(self, weather: open_weather.Weather) -> bool:
        if dt.datetime.now().hour < weather.sunset.hour:
            if weather.wind < self.wind_speed_limit and weather.temperature > self.temperature_limit:
                return True
        return False

    def check_arduino_weather_conditions(self,  weather: arduino_weather.AverageWeather) -> bool:
        if weather.light > self.light_limit and weather.wind < self.wind_speed_limit:
            return True
        return False

    def check_conditions(self) -> Optional[bool]:
        open_weather_data = open_weather.service.get_weather_data()
        arduino_weather.service.get_weather_data()
        if self.first_opening_time < dt.datetime.now().hour < 21:
            arduino_weather_data = arduino_weather.service.get_average_weather(30)
            if open_weather_data and arduino_weather_data:
                log.info("Checking conditions based on arduino and open weather data")
                if self.check_arduino_weather_conditions(arduino_weather_data) and self.check_open_weather_conditions(open_weather_data):
                    return True
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
        log.info("Deciding on opening and closing blinds")
        conditions = self.check_conditions()
        if conditions is True:
            mqtt.service.publish('mari', self.open_signal_mari)
            mqtt.service.publish('pisti', self.open_signal_pisti)
        elif conditions is False:
            mqtt.service.publish('mari', self.close_signal_mari)
            mqtt.service.publish('pisti', self.close_signal_pisti)


controller = MainController(name='MainController')
