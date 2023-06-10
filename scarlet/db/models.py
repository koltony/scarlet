from sqlalchemy import create_engine, ForeignKey, Column, String, Integer, DateTime, Float, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
import datetime as dt

Base = declarative_base()


class ArduinoWeatherModel(Base):
    __tablename__ = 'arduino_weather'

    timestamp = Column('Timestamp', DateTime, primary_key=True)
    wind = Column('Wind', Float)
    light = Column('Light', Integer)
    rain = Column('Rain', Integer)

    def __init__(self, timestamp: dt.datetime, wind: float, light: int, rain: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timestamp = timestamp
        self.wind = wind
        self.light = light
        self.rain = rain

    def __repr__(self):
        return f"ArduinoWeather(timestamp = {self.timestamp}, wind={self.wind}, light={self.light}, rain={self.rain})"


class OpenWeatherModel(Base):
    __tablename__ = 'open_weather'

    timestamp = Column('timestamp', DateTime, primary_key=True)
    temperature = Column('Temperature', Float)
    wind = Column('Wind', Float)
    clouds = Column('Clouds', Float)
    pressure = Column('Pressure', Float)
    humidity = Column('Humidity', Float)
    timezone = light = Column('Light', Integer)
    sunrise = Column('Sunrise', DateTime)
    sunset = Column('Sunset', DateTime)

    def __init__(
        self,
        timestamp: dt.datetime,
        temperature: float,
        wind: float,
        clouds: float,
        pressure: float,
        humidity: float,
        timezone: int,
        sunrise: dt.datetime,
        sunset: dt.datetime,
        *args, **kwargs
         ):
        super().__init__(*args, **kwargs)
        self.timestamp = timestamp
        self.temperature = temperature
        self.wind = wind
        self.clouds = clouds
        self.pressure = pressure
        self.humidity = humidity
        self.timezone = timezone
        self.sunrise = sunrise
        self.sunset = sunset

    def __repr__(self):
        return f"OpenWeather(" \
               f" timestamp={self.timestamp}" \
               f" temperature={self.temperature}," \
               f" wind={self.wind}," \
               f" clouds={self.clouds}," \
               f" pressure={self.pressure}" \
               f" humidity={self.humidity}" \
               f" timezone={self.timezone}" \
               f" sunrise={self.sunrise}" \
               f" sunset={self.sunset})"


class IrrigationDataModel(Base):
    __tablename__ = 'irrigation_data'

    scheduled_time = Column("ScheduledTime", DateTime, primary_key=True)
    should_run = Column("ShouldRun", Boolean)
    is_normal_run = Column("IsNormalRun", Boolean)
    is_started = Column("IsStarted", Boolean)

    def __init__(self, scheduled_time: str,  should_run: bool = True, is_normal_run: bool = True, is_started: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scheduled_time = scheduled_time
        self.should_run = should_run
        self.is_normal_run = is_normal_run
        self.is_started = is_started

    def __repr__(self):
        return f"IrrigationData(" \
               f"scheduled_time={self.scheduled_time}," \
               f" should_run={self.should_run}," \
               f" is_normal_run={self.is_normal_run}," \
               f" is_started={self.is_started} )"
