import datetime as dt
import core.log as log_
from typing import Optional
from sqlmodel import Session, SQLModel, create_engine, select, Field

log = log_.service.logger("models")


class ArduinoWeatherData(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: dt.datetime = Field(default=dt.datetime.now())
    wind: int
    light: int
    rain: int


class OpenWeatherData(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: dt.datetime = Field(default=dt.datetime.now())
    temperature: float
    wind: float
    clouds: float
    pressure: float
    humidity: float
    timezone: int
    sunrise: dt.datetime
    sunset: dt.datetime


class IrrigationData(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: dt.datetime = Field(default=dt.datetime.now())
    zone1: int = 0
    zone2: int = 0
    zone3: int = 0
    zone_connected: int = 0
