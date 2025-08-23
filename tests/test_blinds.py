# import pytest
# import pytest_assume
# import datetime
# from unittest.mock import patch, MagicMock
# import services.blinds as blinds
# import services.open_weather as open_weather
# from db.models import OpenWeatherData
# import core.log as log_

# log = log_.service.logger('test_blinds')


# @pytest.fixture
# def mock_current_time():
#     with patch('datetime.datetime') as mock_datetime:
#         yield mock_datetime


# @pytest.fixture
# def mock_external_service():
#     with patch.object(open_weather.OpenWeatherService, 'get_weather_data') as mock_method:
#         yield mock_method


# @pytest.mark.parametrize("current_time, light_intensity", [
#     (datetime.datetime(year=2023, month=6, day=22, hour=11, minute=0), 2700),
#     (datetime.datetime(year=2023, month=6, day=22, hour=12, minute=0), 2700),
#     (datetime.datetime(year=2023, month=6, day=22, hour=13, minute=0), 2700),
#     (datetime.datetime(year=2023, month=6, day=22, hour=14, minute=0), 2700),
#     (datetime.datetime(year=2023, month=6, day=22, hour=18, minute=0), 2700),
#     (datetime.datetime(year=2023, month=6, day=22, hour=19, minute=0), 2700)
# ])
# def test_adjust_light_intensity(current_time: datetime.datetime, light_intensity: int):
#     mock_current_time.now.return_value = datetime.datetime(2024, 3, 21, 12, 0, 0)
#     open_weather_data = OpenWeatherData(
#             id=1,
#             timestamp=datetime.datetime.now(),
#             temperature=21,
#             wind=30,
#             clouds=0,
#             pressure=1000,
#             humidity=50,
#             timezone=3600,
#             sunrise=current_time.replace(hour=5),
#             sunset=current_time.replace(hour=19))
#     mock_external_service.return_value = MagicMock(return_value=open_weather_data)

#     value = blinds.service._adjust_light_intensity(light_intensity=light_intensity)
#     breakpoint()

