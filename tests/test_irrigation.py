import datetime as dt
from unittest.mock import patch
from scarlet.services import irrigation
from scarlet.services.open_weather import WeatherStatistics as OpenWAverage
from scarlet.core import log as log_

log = log_.service.logger('test_controller')


def mocked_get_hourly_average_weather_for_last_day():
    return {1: OpenWAverage(temperature=22, wind=0, clouds=0, humidity=60, pressure=3000, span=dt.timedelta(hours=1)),
            2: OpenWAverage(temperature=20, wind=0, clouds=0, humidity=60, pressure=3000, span=dt.timedelta(hours=1)),
            3: OpenWAverage(temperature=18, wind=0, clouds=0, humidity=60, pressure=3000, span=dt.timedelta(hours=1))}


def test_irrigation_score_calculation():
    with patch(target="open_weather.service.get_hourly_average_weather_for_last_day", new=mocked_get_hourly_average_weather_for_last_day):
        log.info(irrigation.service.calculate_score())

