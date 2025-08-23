import os
import datetime as dt
import schedule
from sqlmodel import select, delete
import polars as pl

from scarlet.core import log as log_, config
from scarlet.services import open_weather, arduino_weather
from scarlet.db.models import IrrigationSession, IrrigationProgram, IrrigationProgramSession
from scarlet.db.db import service as db_service
from scarlet.api.schemas import IrrigationPydanticSchema

log = log_.service.logger('irrigation')


class IrrigationController(config.Controller):
    _irrigation_status: dict[str, str | int] = {'zone1': 0, 'zone2': 0, 'zone3': 0, 'zone_connected': 0, 'active': 'off'}
    _scheduled_sessions: list[IrrigationProgramSession] = list()
    _scheduled_jobs: list[schedule.Job] = list()
    automation: bool

    def schedule_jobs(self):
        log.debug("Scheduling Irrigation jobs")
        if self.automation: 
            self._scheduled_jobs.append(schedule.every().day.at("03:30").do(self.scheduling_programs))

    @staticmethod
    def calculate_score() -> float:
        log.info("Calculating score for irrigation run")
        vapour_df = pl.read_csv(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../resources", "vapour.csv")).unpivot(index="C", variable_name="humidity", value_name="VPD").with_columns([pl.col("humidity").cast(pl.Int32)])
        weather_df = pl.from_dicts([data.model_dump() for data in open_weather.service.get_history(dt.datetime.now())])
        weather_df = weather_df.with_columns(pl.col('temperature_2m').cast(pl.Int16).clip(lower_bound=6, upper_bound=35), ((pl.col('relative_humidity_2m') / 5).cast(pl.Int16) * 5).clip(lower_bound=5))
        weather_df = vapour_df.join(weather_df, left_on='C', right_on='temperature_2m')[['VPD', 'wind_speed_10m']]
        weather_df.with_columns((pl.col('VPD') + (pl.col('wind_speed_10m') * 0.03)).alias('score'))
        log.debug(f"Calculating average score based on {weather_df['score']}")
        score = weather_df['score'].mean()
        log.debug(f"Calculated score: {score}")
        return score

    def scheduling_programs(self):
        log.info("making decision of irrigation run")
        score = self.calculate_score()
        last_session: IrrigationSession = db_service.get_last(IrrigationSession)
        log.debug(f"last_session: {last_session}")
        programs = db_service.session.exec(select(IrrigationProgram).where(IrrigationProgram.is_active is True)).all()
        log.debug("retreived programs: {programs}")

        self._scheduled_sessions = list()
        scheduled_programs: list[IrrigationProgram] = list()
        for program in programs:
            if program.lower_score < score < program.upper_score: 
                if last_session is None or (((last_session.timestamp - dt.datetime(last_session.timestamp.year,1,1,0)).days >= program.frequency)):
                    scheduled_programs.append(program)
                    for session in program.sessions:
                        scheduled = schedule.every().day.at(session.start_time.strftime("%H:%M")).do(self.run_scheduled_session, session=session)
                        scheduled.cancel_after(dt.datetime(dt.date.today().year, dt.date.today().month, dt.date.today().day,  session.start_time.hour + 1))
                        log.debug(f"scheduled session: {scheduled}")
                        self._scheduled_sessions.append(scheduled)

        if len(scheduled_programs) > 1:
            log.warning(f"scheduled {len(scheduled_programs)} programs")
        elif len(scheduled_programs) == 0:
            log.info("no programs were scheduled")

    def run_scheduled_session(self, session: IrrigationProgramSession) -> None:
        weather = arduino_weather.service.get_current_weather()
        if weather and weather.rain == 1:
            log.info("rained before irrigation session, skipping scheduled run")
            return
        log.info(f"started irrigation with {session}")
        self._irrigation_status = IrrigationPydanticSchema.model_validate(session).model_dump()

    def get_program(self):
        return self._irrigation_status

    def set_irrigation_program(self, progam: IrrigationProgram):
        log.info(f"adding program {progam} to database")
        db_service.add(progam)

    def update_irrigation_program(self, progam: IrrigationProgram):
        log.info(f"updating program {progam}")
        db_service.add(progam)

    def update_irrigation_session(self, session: IrrigationProgramSession):
        log.info(f"updating session {session}")
        db_service.add(session)

    def get_irrigation_programs(self) -> list[IrrigationProgram]:
        programs = db_service.session.exec(select(IrrigationProgram)).all()
        log.info(f"retreived program {programs}")
        return programs

    def get_irrigation_program_by_id(self, program_id: int) -> IrrigationProgram:
        program = db_service.session.exec(select(IrrigationProgram).where(IrrigationProgram.id == program_id)).first()
        log.info(f"retreived program {program}")
        return program

    def delete_irrigation_program_by_id(self, program_id: int):
        db_service.session.exec(delete(IrrigationProgram).where(IrrigationProgram.id == program_id))
        db_service.session.commit()
        log.info(f"Deleted program {program_id}")

    def get_session_by_id(self, session_id: int) -> IrrigationProgramSession:
        session = db_service.session.exec(select(IrrigationProgramSession).where(IrrigationProgramSession.id == session_id)).first()
        log.info(f"retreived session {session}")
        return session

    def set_automation(self, state: bool):
        self.automation = state
        if state is False:
            log.debug(f'cancelling {len(self._scheduled_jobs)} scheduled jobs and {len(self._scheduled_sessions)} irrigation sessions')
            [schedule.cancel_job(j) for j in self._scheduled_jobs]
            self._scheduled_jobs = list()
            [schedule.cancel_job(j) for j in self._scheduled_sessions]
            self._scheduled_sessions = list()
        self._self_edit_config(attribute='automation', new_value=state)