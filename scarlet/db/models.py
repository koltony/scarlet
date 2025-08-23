import datetime as dt
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from scarlet.core import log as log_

log = log_.service.logger("models")


class ArduinoWeatherData(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: dt.datetime = Field(default=dt.datetime.now())
    wind: int
    light: int
    rain: int


class Weather(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: dt.datetime
    temperature_2m: float
    relative_humidity_2m: float
    cloud_cover: float
    precipitation: float
    precipitation_probability: float
    wind_speed_10m: float
    wind_gusts_10m: float

class HistoricalWeather(Weather, table=True):
    pass

class ForecastedWeather(Weather, table=True):
    pass


class IrrigationSessionBase(SQLModel, table=False):
    id: Optional[int] = Field(default=None, primary_key=True)
    zone1: int = 0
    zone2: int = 0
    zone3: int = 0
    zone_connected: int = 0


class IrrigationSession(IrrigationSessionBase, table=True):
    timestamp: dt.datetime = Field(default=dt.datetime.now())


class IrrigationProgramSession(IrrigationSessionBase, table=True):
    program_id: Optional[int] = Field(default=None, foreign_key="irrigationprogram.id")
    program: Optional["IrrigationProgram"] = Relationship(back_populates="sessions")
    start_time: dt.time


class IrrigationProgram(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    is_active: bool = True

    sessions: list[IrrigationProgramSession] = Relationship(back_populates="program")
    frequency: int
    lower_score: float
    upper_score: float

class BlindAction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: dt.datetime = Field(default=dt.datetime.now())
    is_user: bool
    is_left_up: bool
    is_right_up: bool
