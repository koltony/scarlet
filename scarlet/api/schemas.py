from pydantic import BaseModel, field_validator
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

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            value = value.lower()
            for member in cls:
                if member.value == value:
                    return member
        return None


class BlindsSettingLightLimitSchema(BaseModel):
    limit: int


class AutomationState(BaseModel):
    automation: bool


class BlindsPydanticSchema(BaseModel):
    left_blind: BlindState
    right_blind: BlindState


class IrrigationSessionSchema(BaseModel):
    zone1: int = 0
    zone2: int = 0
    zone3: int = 0
    zone_connected: int = 0


class IrrigationRunSessionSchema(IrrigationSessionSchema):
    active: IrrigationState

class HistoricalIrrigationRunSessionSchema(IrrigationRunSessionSchema):
    timestamp: dt.datetime


class IrrigationUpdateProgramSessionSchema(BaseModel):
    start_time: dt.time | None = None
    zone1: int | None = None
    zone2: int | None = None
    zone3: int | None = None
    zone_connected: int | None

    @field_validator("start_time", mode="before")
    def format_start_time(cls, value):
        if isinstance(value, dt.time):
            return value.strftime("%H:%M")
        return value

class IrrigationGetProgramSessionSchema(IrrigationUpdateProgramSessionSchema):
    id: int


class IrrigationUpdateProgramSchema(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    sessions: list[IrrigationUpdateProgramSessionSchema] | None = None
    frequency: int | None = None
    lower_score: float | None = None
    upper_score: float | None = None


class IrrigationGetProgramSchema(IrrigationUpdateProgramSchema):
    id: int
    sessions: list[IrrigationGetProgramSessionSchema]


class IrrigationCreateProgramSessionSchema(IrrigationSessionSchema):
    start_time: dt.time


class IrrigationCreateProgramSchema(BaseModel):
    name: str
    is_active: bool

    sessions: list[IrrigationCreateProgramSessionSchema] | None = None
    frequency: int
    lower_score: float
    upper_score: float
