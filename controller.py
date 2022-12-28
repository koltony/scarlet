import schedule
import diskcache
from typing import Optional
import datetime as dt
import weather
import config
import time
import mqtt
import log as log_

log = log_.service.logger('controller')


class MainController(config.Component):

    def __init__(self, name):
        super().__init__(name=name)
        self.retry_amounts = 10  # type: int

        self.IrrigationController = IrrigationController('IrrigationController')
        self.BlindsController = BlindsController('BlindsController')

    def start_process(self):
        self.test_services()
        schedule.every().day.do(weather.service.clear_old_cache_data())
        self.schedule_blinds_jobs()
        self.schedule_irrigation_jobs()

    def test_services(self):
        time.sleep(1)
        log.info("Starting MainController test")
        for i in range(self.retry_amounts):
            log.info(f"Test round {i + 1}")
            try:
                mqtt.service.publish(topic='test', payload='mqtt tester message')
                time.sleep(1)
                if mqtt.service.get_message(topic='test') is not None:
                    log.info("mqtt test passed")
                    break
            except Exception as e:
                log.warning(f"{i + 1} test have failed with error")
            log.warning(f"{i + 1} test have failed with response issue")

    def schedule_blinds_jobs(self):
        log.debug("scheduling blinds related jobs")
        schedule.every(15).minutes.do(self.BlindsController.decide_opening_and_closing())
        schedule.every().minute.do(self.BlindsController.emergency_close_test())
        schedule.every(10).minutes.do(self.BlindsController.checkin_to_eclipse_arduino)

    def schedule_irrigation_jobs(self):
        schedule.every().day.at("2:00").do(self.IrrigationController.decide_irrigation())


class IrrigationData:
    def __init__(self, scheduled_time: dt.datetime, is_rained: bool=False):
        self.scheduled_time = scheduled_time
        self.is_rained = is_rained


class IrrigationController(config.Component):

    def __init__(self, name):
        super().__init__(name=name)
        self.start_time = None  # type: Optional[str]
        self.recalculation_time = None  # type: Optional[str]
        self.cache_directory = None  # type: Optional[str]
        self.cache = None  # type: Optional[diskcache.Cache]

    def initialize(self):
        with diskcache.Cache(directory=self.cache_directory) as cache:
            self.cache = cache

    def decide_irrigation(self):
        if mqtt.service.get_message('rain') == 0:  # Not yet implemented
            data = weather.service.get_average_weather(5)
            if data.temperature < 5:
                log.info("Irrigation will not run due low average temperature")
                self.cache[f"{dt.date.today().strftime('%Y/%m/%d')}_irrigation"] = IrrigationData(dt.datetime.now(), False)
        else:
            log.info("Irrigation will not run due to enough rain")
            self.cache[f"{dt.date.today().strftime('%Y/%m/%d')}_irrigation"] = IrrigationData(dt.datetime.now(), True)

    @staticmethod
    def irrigation_process():
        mqtt.service.publish('zone1', 1)
        mqtt.service.publish('zone2', 1)
        mqtt.service.publish('zone3', 0)
        mqtt.service.publish('zone_connected', 1)
        mqtt.service.publish('active', 1)


class BlindsController(config.Component):

    def __init__(self, name):
        super().__init__(name=name)
        self.stop_signal_mari = None
        self.open_signal_mari = None
        self.close_signal_mari = None

        self.stop_signal_pisti = None
        self.open_signal_pisti = None
        self.close_signal_pisti = None

        self.absolute_wind_speed_limit = None
        self.wind_speed_limit = None
        self.temperature_limit = None
        self.cloud_coverage_limit = None
        self.first_opening_time = None

    @staticmethod
    def checkin_to_eclipse_arduino():
        return mqtt.service.publish('eclipse_checkin', 'connected')

    def emergency_close_test(self):
        wind_speed = mqtt.service.get_message('wind')
        if wind_speed:
            if wind_speed >= self.absolute_wind_speed_limit:
                mqtt.service.publish('mari', self.close_signal_mari)
                mqtt.service.publish('pisti', self.close_signal_pisti)
            else:
                log.warning("Wind data not available")

    def check_conditions(self) -> bool:
        weather_conditions = weather.service.get_weather_data()
        wind_data = mqtt.service.get_message('wind')
        if self.first_opening_time < dt.datetime.now().hour < weather_conditions.sunset.hour:
            if weather_conditions.temperature > self.temperature_limit and \
                    (max(wind_data, weather_conditions.wind) < self.wind_speed_limit) and \
                    (weather_conditions.clouds < self.cloud_coverage_limit):

                log.info(f"Blinds can go down. "
                         f"temp: {weather_conditions.temperature}C,"
                         f" wind: ({wind_data}, {weather_conditions.wind}) km/h ,"
                         f" clouds: {weather_conditions.clouds})")
                return True

        return False

    def decide_opening_and_closing(self):
        if self.check_conditions() is True:
            mqtt.service.publish('mari', self.open_signal_mari)
            mqtt.service.publish('pisti', self.open_signal_pisti)
        else:
            mqtt.service.publish('mari', self.close_signal_mari)
            mqtt.service.publish('pisti', self.close_signal_pisti)


controller = MainController(name='MainController')
