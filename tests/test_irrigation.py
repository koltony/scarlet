import pytest
import datetime as dt
from unittest.mock import patch
import services.irrigation as irrigation
import services.open_weather as open_weather
import core.log as log_

log = log_.service.logger('test_controller')


def mocked_get_hourly_average_weather_for_last_day():
    return {1: open_weather.WeatherStatistics(temperature=22, wind=10, clouds=0, humidity=60, pressure=3000, span=dt.timedelta(hours=1))}


def test_irrigation_score_calculation():
    with patch(target="services.open_weather.service.get_hourly_average_weather_for_last_day", new=mocked_get_hourly_average_weather_for_last_day):
        score = irrigation.service.calculate_score()
        # coming from the resources/vapour file
        VPD = 1.06
        assert score == (VPD + (0.03 * 10))


