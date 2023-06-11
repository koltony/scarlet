from pydantic import BaseModel
from enum import Enum
import datetime as dt
import scarlet.core.log as log_

log = log_.service.logger('schemas')


class BlindState(Enum):
    up = 'up'
    down = 'down'
    nostate = 'nostate'


class IrrigationState(Enum):
    on = 'on'
    off = 'off'
    nostate = 'nostate'


class ArduinoWeatherPydanticSchema(BaseModel):
    wind: int
    light: int
    rain: int


class OpenWeatherPydanticSchema(BaseModel):
    temperature: float
    wind: float
    clouds: float
    pressure: float
    humidity: float
    timezone: int
    sunrise: dt.datetime
    sunset: dt.datetime


class BlindsPydanticSchema(BaseModel):
    left_blind: BlindState
    right_blind: BlindState


class IrrigationPydanticSchema(BaseModel):
    zone1: int
    zone2: int
    zone3: int
    zone_connected: int
    active: IrrigationState

