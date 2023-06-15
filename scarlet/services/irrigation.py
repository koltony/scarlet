import statistics
import schedule
import pandas as pd
from typing import Optional, Dict, List
import datetime as dt
import os
from sqlmodel import select

from scarlet.core import log as log_, config
import scarlet.services.open_weather as open_weather
from scarlet.db.models import IrrigationData
from scarlet.db.db import service as db_service
from scarlet.api.schemas import IrrigationPydanticSchema

log = log_.service.logger('irrigation')


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


class IrrigationController(config.Component):

    def __init__(self, name):
        super().__init__(name=name)
        self.Programs = IrrigationPrograms("Programs")
        self._irrigation_status = {'zone1': 0, 'zone2': 0, 'zone3': 0, 'zone_connected': 0, 'active': 'off'}

    def schedule_jobs(self):
        log.debug("Scheduling Irrigation jobs")
        schedule.every().day.at("04:00").do(self.decide_irrigation)
        schedule.every().minute.do(self._check_irrigation_start)

    def _check_irrigation_start(self):
        program = db_service.get_last(IrrigationData)
        if program and program.should_run is True and program.is_started is False:
            now = dt.datetime.now()
            log.debug("Checking irrigation start time")
            log.debug(f"Scheduled hour: {program.scheduled_time.split(':')[0]} now: {now.hour} is {int(program.scheduled_time.split(':')[0]) == now.hour} \n"
                      f"Scheduled minute: {program.scheduled_time.split(':')[1]} now: {now.minute} is {int(program.scheduled_time.split(':')[1]) == now.minute}")
            if int(program.scheduled_time.split(':')[0]) == now.hour and int(program.scheduled_time.split(':')[1]) == now.minute:
                log.info("Starting irrigation program")
                program.is_started = True
                self.run_program(IrrigationPydanticSchema(
                    zone1=program.zone1,
                    zone2=program.zone2,
                    zone3=program.zone3,
                    zone_connected=program.zone_connected,
                    active="on"))

    @staticmethod
    def calculate_score() -> Optional[float]:
        log.info("Calculating score for irrigation run")
        df = pd.read_csv(filepath_or_buffer=os.path.join(os.path.dirname(os.path.realpath(__file__)), "../resources", "vapour.csv"), header=0, index_col=0)
        open_weather_data = open_weather.service.get_hourly_average_weather_for_last_day()
        scores = list()
        if open_weather_data and not df.empty:
            for name, data in open_weather_data.items():
                temperature = int(data.temperature)
                if temperature < 6:
                    temperature = 6
                if temperature > 35:
                    temperature = 35
                humidity = 5 * round(data.humidity / 5)
                VPD = df.at[temperature, str(humidity)]
                scores.append(VPD + (0.03 * data.wind))
            log.debug(f"Calculating average score based on {scores}")
            score = statistics.mean(scores)
            log.debug(f"Calculated score: {score}")
            return score
        log.error("No available score")
        return None

    @staticmethod
    def _get_last_run() -> int:
        log.debug("Get last irrigation run")
        last_run = 7
        programs = db_service.session.exec(select(IrrigationData.timestamp > dt.datetime.now() - dt.timedelta(days=7))).all()
        if programs:
            for program in programs:
                if program.should_run and program.is_normal_run and program.is_started:
                    days_since = (program.timestamp - dt.datetime.now()).days
                    if program.timestamp.seconds > 12 * 3600:
                        days_since += 1
                    if days_since < last_run:
                        last_run = days_since
            log.debug(f"Irrigation system ran {last_run}  days ago")
        return last_run

    def decide_irrigation(self):
        log.info("Making decision on next irrigation run")
        #        if arduino_data:
        #           if arduino_data.rain == 1:
        #                log.info("Its raining outside, turning off irrigation for today")
        #                return
        score = self.calculate_score()
        if score is not None:
            for name, program in self.Programs.scores_for_programs.items():
                if program[0] < score < program[1]:
                    p = getattr(self.Programs, name)
                    last_run = self._get_last_run()
                    log.debug(f"(p.every_x_day){p.every_x_day} <= {last_run} (last_run)")
                    if p.every_x_day <= last_run:
                        log.info(f"Using program: {name} in the next run")
                        sunrise = open_weather.service.get_weather_data().sunrise
                        irrigation_data = IrrigationData(
                            scheduled_time=f"{sunrise.hour}:{sunrise.minute}",
                            should_run=True,
                            is_normal_run=True,
                            zone1=p.zone1,
                            zone2=p.zone2,
                            zone3=p.zone3,
                            zone_connected=p.zone_connected)
                        db_service.session.add(irrigation_data)
                        return
                    irrigation_data = IrrigationData(
                        scheduled_time=f"6:00",
                        should_run=False,
                        is_normal_run=True,
                        zone1=p.zone1,
                        zone2=p.zone2,
                        zone3=p.zone3,
                        zone_connected=p.zone_connected)
                    db_service.session.add(irrigation_data)
                    log.info(f"Program should not run  because this  should only run every 2nd days, last run: {last_run}")
                    return
            log.info("No program should run because of conditions")
            irrigation_data = IrrigationData(scheduled_time=f"6:00")
            db_service.session.add(irrigation_data)
        else:
            log.warning("No weather score data available, using default program for next run")
            irrigation_data = IrrigationData(
                scheduled_time="6:00",
                should_run=True,
                is_normal_run=True,
                zone1=self.Programs.DefaultProgram.zone1,
                zone2=self.Programs.DefaultProgram.zone2,
                zone3=self.Programs.DefaultProgram.zone3,
                zone_connected=self.Programs.DefaultProgram.zone_connected)
            db_service.session.add(irrigation_data)

    def run_program(self, program: IrrigationPydanticSchema):
        self._irrigation_status = program.dict()

    def get_program(self):
        return self._irrigation_status


service = IrrigationController("IrrigationController")
