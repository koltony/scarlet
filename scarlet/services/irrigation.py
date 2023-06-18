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
        self.days_of_keeping_data = config.ConfigOption(required=True).integer  # type: int
        self._irrigation_status = {'zone1': 0, 'zone2': 0, 'zone3': 0, 'zone_connected': 0, 'active': 'off'}

    def schedule_jobs(self):
        log.debug("Scheduling Irrigation jobs")
        schedule.every().day.at("04:00").do(self.decide_irrigation)
        schedule.every().minute.do(self._check_irrigation_start)
        schedule.every().day.do(self._clear_data)

    def _clear_data(self):
        db_service.clear_old_data(IrrigationData, dt.datetime.now() - dt.timedelta(days=self.days_of_keeping_data))

    def _check_irrigation_start(self):
        program = db_service.get_last(IrrigationData)
        if program and program.should_run is True and program.is_started is False:
            now = dt.datetime.now()
            log.debug("Checking irrigation start time")
            log.debug(f"Scheduled time: {program.scheduled_time}, time: {dt.datetime.now()}")
            if program.scheduled_time.hour == now.hour and program.scheduled_time.minute == now.minute:
                log.info("Starting irrigation program")
                program.is_started = True
                db_service.session.refresh(program)
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
        score = self.calculate_score()
        if score is not None:
            for name, program in self.Programs.scores_for_programs.items():
                if program[0] < score < program[1]:
                    p = getattr(self.Programs, name)
                    sunrise = open_weather.service.get_weather_data().sunrise
                    irrigation_data = IrrigationData(
                        scheduled_time=sunrise,
                        schould_run=True if p.every_x_day <= self._get_last_run() else False,
                        is_normal_run=True,
                        zone1=p.zone1,
                        zone2=p.zone2,
                        zone3=p.zone3,
                        zone_connected=p.zone_connected)
                    db_service.session.add(irrigation_data)
                    log.info(f"Using program: {name} [{irrigation_data}] in the next run")
                    return
            log.info(f"no program will run because of conditions, score: {score}")
        else:
            log.warning("No weather score data available, using default program for next run")
            irrigation_data = IrrigationData(
                scheduled_time=dt.datetime.now().replace(hour=6, minute=0),
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
