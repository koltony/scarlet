import pytest
import pytest_assume
import datetime
from unittest.mock import patch
import services.blinds as blinds
import core.log as log_

log = log_.service.logger('test_blinds')


def test_adjust_light_intensity():
    light_intensities_by_time = {
        datetime.datetime(year=2023, month=6, day=22, hour=11, minute=0): 2700,
        datetime.datetime(year=2023, month=6, day=22, hour=12, minute=0): 2700,
        datetime.datetime(year=2023, month=6, day=22, hour=13, minute=0): 2700,
        datetime.datetime(year=2023, month=6, day=22, hour=14, minute=0): 2700,
        datetime.datetime(year=2023, month=6, day=22, hour=18, minute=0): 2700,
        datetime.datetime(year=2023, month=6, day=22, hour=19, minute=0): 2700
    }
    adjusted_lights_by_hour = dict()
    for time, intensity in light_intensities_by_time.items():
        adjusted_lights_by_hour[time.hour] = blinds.service._adjust_light_intensity(light_intensity=intensity, now=time)
    pytest.assume(adjusted_lights_by_hour[12] == 2700)
    pytest.assume(adjusted_lights_by_hour[11] > adjusted_lights_by_hour[12])
    pytest.assume(adjusted_lights_by_hour[18] > adjusted_lights_by_hour[14] > adjusted_lights_by_hour[13] > adjusted_lights_by_hour[12])
    pytest.assume(adjusted_lights_by_hour[18] == adjusted_lights_by_hour[19])

