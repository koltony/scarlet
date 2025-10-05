import statistics
import datetime as dt
import schedule
from sqlmodel import select

from scarlet.core import log as log_, config
from scarlet.db.models import ArduinoWeatherData
from scarlet.db.db import service as db_service

log = log_.service.logger('ardu_weather')



class ArduinoWeather(config.Service):
    class Config(config.Service.Config):
        anemometer_milli_volt_out_min: int
        anemometer_milli_volt_out_max: int
        anemometer_max_meter_per_sec: float
        arduino_max_milli_input_voltage: int
        arduino_input_resolution: int

        save_frequency: int
        local_cache_size: int

    config: 'ArduinoWeather.Config'
    _weather: list[ArduinoWeatherData] = list()
    def schedule_jobs(self):
        schedule.every(self.config.save_frequency).minutes.do(self.save_weather_data)

    def _value_to_wind_speed(self, value) -> float:
        """"Converts arduino analog read value to actual wind speed"""
        milli_volt_per_value = self.config.arduino_input_resolution / self.config.arduino_max_milli_input_voltage
        delta_voltage = self.config.anemometer_milli_volt_out_max - self.config.anemometer_milli_volt_out_min
        meter_per_sec_per_voltage = delta_voltage / self.config.anemometer_max_meter_per_sec  # mps/mV
        value_voltage = value * milli_volt_per_value
        log.debug(f"wind sensor voltage: {value_voltage} mV")
        if value_voltage < self.config.anemometer_milli_volt_out_min:
            log.debug(f"voltage: {value_voltage} is under threshold: {self.config.anemometer_milli_volt_out_min} returning 0")
            return 0.0

        meter_per_sec = (value_voltage - self.config.anemometer_milli_volt_out_min) / meter_per_sec_per_voltage
        km_per_hour = round(meter_per_sec * 3.6, 1)
        log.debug(f"calculated wind speed: {km_per_hour}")
        return km_per_hour


    def append_weather_data(self, weather: ArduinoWeatherData) -> None:
        log.debug(f"got weather data from arduino : {weather}")
        weather.wind = self._value_to_wind_speed(weather.wind)
        self._weather.append(weather)
        self._weather = self._weather[-self.config.local_cache_size:]

    def save_weather_data(self) -> None:
        if self._weather:
            db_service.add(
                ArduinoWeatherData(
                    wind = statistics.median([w.wind for w in self._weather]),
                    light_1 = statistics.median([w.light_1 for w in self._weather]),
                    light_2 = statistics.median([w.light_2 for w in self._weather]),
                    rain = self._weather[-1].rain
                    )
                )
        else:
            log.warning("no data available to save")

    def get_history(self, time: dt.datetime) -> list[ArduinoWeatherData]:
        return db_service.session.exec(select(ArduinoWeatherData).where(ArduinoWeatherData.timestamp > time)).all()

    def get_current_weather(self) -> ArduinoWeatherData | None:
        if self._weather:
            return ArduinoWeatherData(
                wind = statistics.median([w.wind for w in self._weather]),
                light_1 = statistics.median([w.light_1 for w in self._weather]),
                light_2 = statistics.median([w.light_2 for w in self._weather]),
                rain = self._weather[-1].rain
                )


service = ArduinoWeather('ArduinoWeatherService')
