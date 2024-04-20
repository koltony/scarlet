import statistics
import schedule
import pandas as pd
from typing import Optional, Dict, List
import datetime as dt
import os
from sqlmodel import select

from core import log as log_, config
import services.open_weather as open_weather
from db.models import IrrigationData
from db.db import service as db_service
from api.schemas import IrrigationPydanticSchema

log = log_.service.logger('irrigation')


class IrrigationProgram(config.Component):
    def __init__(self, name):
        super().__init__(name=name)
        self.scores = config.ConfigOption(required=True).list  # type: Optional[List[int]]
        self.zone1 = config.ConfigOption(required=True).integer  # type: int
        self.zone2 = config.ConfigOption(required=True).integer  # type: int
        self.zone3 = config.ConfigOption(required=True).integer  # type: int
        self.zone_connected = config.ConfigOption(required=True).integer  # type: int
        self.every_x_day = config.ConfigOption(required=True).integer  # type: int

    def __str__(self):
        return f"{self.name}(scores: {self.scores})"


class IrrigationPrograms(config.Component):
    def __init__(self, name):
        super().__init__(name=name)
        self.Program_1 = IrrigationProgram("Program_1")
        self.Program_2 = IrrigationProgram("Program_2")
        self.Program_3 = IrrigationProgram("Program_3")
        self.Program_4 = IrrigationProgram("Program_4")
        self.programs = [self.Program_1, self.Program_2, self.Program_3, self.Program_4]


class IrrigationController(config.Component):

    def __init__(self, name):
        super().__init__(name=name)
        self.Programs = IrrigationPrograms("Programs")
        self.days_of_keeping_data = config.ConfigOption(required=True).integer  # type: int
        self._irrigation_status = {'zone1': 0, 'zone2': 0, 'zone3': 0, 'zone_connected': 0, 'active': 'off'}

    def schedule_jobs(self):
        log.debug("Scheduling Irrigation jobs")
        schedule.every().day.at("06:30").do(self.decide_irrigation)
        schedule.every().day.do(self._clear_data)

    def _clear_data(self):
        db_service.clear_old_data(IrrigationData, dt.datetime.now() - dt.timedelta(days=self.days_of_keeping_data))

    @staticmethod
    def calculate_score() -> float:
        log.info("Calculating score for irrigation run")
        df = pd.read_csv(filepath_or_buffer=os.path.join(os.path.dirname(os.path.realpath(__file__)), "../resources", "vapour.csv"), header=0, index_col=0)
        open_weather_data = open_weather.service.get_hourly_average_weather_for_last_day()
        scores = list()
        for name, data in open_weather_data.items():
            temperature = int(data.temperature)
            humidity = int(data.humidity/5) * 5
            if temperature < 6:
                temperature = 6
            if temperature > 35:
                temperature = 35
            VPD = df.at[temperature, str(humidity)]
            scores.append(VPD + (0.03 * data.wind))
        log.debug(f"Calculating average score based on {scores}")
        score = statistics.mean(scores)
        log.debug(f"Calculated score: {score}")
        return score

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
        log.info("Making decision of irrigation run")
        score = self.calculate_score()
        last_program: IrrigationData = db_service.get_last(IrrigationData)
        for program in self.Programs.programs:
            if program.scores[0] < score < program.scores[1] and (last_program is None or (dt.datetime.now() - last_program.timestamp) >= (dt.timedelta(hours=23, minutes=50) * program.every_x_day)):
                irrigation_data = IrrigationData(
                    zone1=program.zone1,
                    zone2=program.zone2,
                    zone3=program.zone3,
                    zone_connected=program.zone_connected)
                db_service.add(irrigation_data)
                self.run_program(IrrigationPydanticSchema(
                    zone1=program.zone1,
                    zone2=program.zone2,
                    zone3=program.zone3,
                    zone_connected=program.zone_connected,
                    active='on'))
                log.info(f"using program: {program.name} [{program}] for run")
                return
        log.info(f"no program will run because of conditions, score: {score} and day diff: {(dt.datetime.now() - last_program.timestamp)}")

    def run_program(self, program: IrrigationPydanticSchema):
        log.info(f"started irrigation wit {program}")
        self._irrigation_status = program.dict()

    def get_program(self):
        return self._irrigation_status


service = IrrigationController("IrrigationController")
