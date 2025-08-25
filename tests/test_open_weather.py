import datetime as dt
import pytest
from unittest.mock import MagicMock, patch
import polars as pl

from scarlet.db.db import service as db_service
from scarlet.db.models import Weather, ForecastedWeather, HistoricalWeather
from scarlet.services.open_weather import OpenWeatherService


@pytest.fixture
def service():
    return OpenWeatherService("OpenWeatherService")


def make_mock_response(json_data):
    mock_resp = MagicMock()
    mock_resp.json.return_value = json_data
    return mock_resp


def test_cache_historic_data_no_last_point(service):
    fake_hourly = {
        "time": [dt.datetime(2025, 1, 1, 0, 0)],
        "temperature_2m": [10],
        "relative_humidity_2m": [50],
        "cloud_cover": [20],
        "precipitation": [0],
        "precipitation_probability": [0],
        "wind_speed_10m": [5],
        "wind_gusts_10m": [7],
    }
    with patch("requests.get", return_value=make_mock_response({"hourly": fake_hourly})), \
         patch.object(db_service, "get_last", return_value=None), \
         patch.object(db_service, "add_all") as mock_add:
        service._cache_historic_data()
        assert mock_add.called
        # Ensure HistoricalWeather objects were created
        args, _ = mock_add.call_args
        assert all(isinstance(x, HistoricalWeather) for x in args[0])


def test_cache_historic_data_with_last_point_filters(service):
    fake_hourly = {
        "time": [dt.datetime(2025, 1, 1, 0, 0), dt.datetime(2025, 1, 2, 0, 0)],
        "temperature_2m": [10, 12],
        "relative_humidity_2m": [50, 55],
        "cloud_cover": [20, 30],
        "precipitation": [0, 1],
        "precipitation_probability": [0, 10],
        "wind_speed_10m": [5, 6],
        "wind_gusts_10m": [7, 8],
    }
    last_point = HistoricalWeather(timestamp=dt.datetime(2025, 1, 1, 12, 0))
    with patch("requests.get", return_value=make_mock_response({"hourly": fake_hourly})), \
         patch.object(db_service, "get_last", return_value=last_point), \
         patch.object(db_service, "add_all") as mock_add:
        service._cache_historic_data()
        args, _ = mock_add.call_args
        # Only later timestamps should remain
        assert all(dp.timestamp > last_point.timestamp for dp in args[0])


def test_cache_forecasted_weather_data(service):
    fake_hourly = {
        "time": [dt.datetime(2025, 1, 1, 0, 0)],
        "temperature_2m": [10],
        "relative_humidity_2m": [50],
        "cloud_cover": [20],
        "precipitation": [0],
        "precipitation_probability": [0],
        "wind_speed_10m": [5],
        "wind_gusts_10m": [7],
    }
    with patch("requests.get", return_value=make_mock_response({"hourly": fake_hourly})), \
         patch.object(db_service, "clear_data_after") as mock_clear, \
         patch.object(db_service, "add_all") as mock_add:
        service._cache_forecasted_weather_data()
        assert mock_clear.called
        assert mock_add.called
        args, _ = mock_add.call_args
        assert all(isinstance(x, ForecastedWeather) for x in args[0])


def test_cache_sun_data(service):
    sunset_str = "2025-01-01T17:00:00"
    sunrise_str = "2025-01-02T06:00:00"
    with patch("requests.get", return_value=make_mock_response({
        "daily": {"sunset": [sunset_str], "sunrise": [sunrise_str]}
    })):
        service._cache_sun_data()
        assert service.sunset_time == dt.datetime.fromisoformat(sunset_str)
        assert service.sunrise_time == dt.datetime.fromisoformat(sunrise_str)


def test_get_current_data_success(service):
    fake_current = {
        "time": [dt.datetime(2025, 1, 1, 0, 0)],
        "temperature_2m": [10],
        "relative_humidity_2m": [50],
        "cloud_cover": [20],
        "precipitation": [0],
        "precipitation_probability": [0],
        "wind_speed_10m": [5],
        "wind_gusts_10m": [7],
    }
    with patch("requests.get", return_value=make_mock_response({"current": fake_current})):
        result = service.get_current_data()
        assert isinstance(result, Weather)


def test_get_current_data_fallback(service):
    hist = HistoricalWeather(timestamp=dt.datetime(2025, 1, 1, 0, 0))
    with patch("requests.get", side_effect=Exception("fail")), \
         patch.object(db_service, "get_last", return_value=hist):
        result = service.get_current_data()
        assert result == hist


def test_get_closest_history_and_get_history(service):
    fake_exec = MagicMock()
    fake_exec.first.return_value = "closest"
    fake_exec.all.return_value = ["h1", "h2"]
    fake_session = MagicMock()
    fake_session.exec.return_value = fake_exec

    with patch.object(db_service, "session", fake_session):
        assert service.get_closest_history(dt.datetime.now()) == "closest"
        assert service.get_history(dt.datetime.now()) == ["h1", "h2"]
