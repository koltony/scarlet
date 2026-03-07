import statistics
import datetime as dt
import schedule
from sqlmodel import select
import json

from scarlet.core import log as log_, config, mqtt_module
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

    def initialize(self):
        mqtt_module.register_subscription("home/weather", self.append_weather_data)
        log.debug("will subscribe to home/weather for weather data from arduino")

    def schedule_jobs(self):
        schedule.every(self.config.save_frequency).minutes.do(self.save_weather_data)

    def _value_to_wind_speed(self, value) -> float:
        """"Converts arduino analog read value to actual wind speed"""

        log.info(f"raw wind speed: {value}")
        milli_volt_per_value = self.config.arduino_max_milli_input_voltage / self.config.arduino_input_resolution
        delta_voltage = self.config.anemometer_milli_volt_out_max - self.config.anemometer_milli_volt_out_min
        meter_per_sec_per_voltage = delta_voltage / self.config.anemometer_max_meter_per_sec  # mps/mV
        value_voltage = value * milli_volt_per_value
        log.debug("wind sensor voltage: %s mV", value_voltage)
        if value_voltage < self.config.anemometer_milli_volt_out_min:
            log.debug("voltage: %s is under threshold: %s returning 0", value_voltage, self.config.anemometer_milli_volt_out_min)
            return 0.0

        meter_per_sec = (value_voltage - self.config.anemometer_milli_volt_out_min) / meter_per_sec_per_voltage
        km_per_hour = round(meter_per_sec * 3.6, 1) * 6 # compared with official wind data, we are getting a much lower value
        log.debug("calculated wind speed: %s km/h", km_per_hour)
        return km_per_hour

    def append_weather_data(self, client, userdata, msg):
        data = json.loads(msg.payload.decode())
        weather = ArduinoWeatherData(**data)
        log.debug("got weather data from arduino : %s", weather)
        weather.raw_wind = weather.wind
        weather.wind = self._value_to_wind_speed(weather.wind)
        self._weather.append(weather)
        self._weather = self._weather[-self.config.local_cache_size:]

    def save_weather_data(self) -> None:
        if self._weather:
            db_service.add(
                ArduinoWeatherData(
                    wind = statistics.median([w.wind for w in self._weather]),
                    raw_wind = statistics.median([w.raw_wind for w in self._weather]),
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
                raw_wind = statistics.median([w.raw_wind for w in self._weather]),
                light_1 = statistics.median([w.light_1 for w in self._weather]),
                light_2 = statistics.median([w.light_2 for w in self._weather]),
                rain = self._weather[-1].rain
                )


service = ArduinoWeather('ArduinoWeatherService')
