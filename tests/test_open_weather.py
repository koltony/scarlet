import datetime as dt
from typing import Any
import pytest
import pytest_assume
from scarlet.core import config
from scarlet.services import open_weather


@pytest.mark.parametrize("cfg", [
    (
        {
            "services":
                {
                    "OpenWeatherService": None,
                    "Database": {
                        "database": 'test.db'
                    }
                }
        }
    )
])
def test_get_weather_data(cfg: dict[str, Any]):
    config.Process.configure_all(cfg)
    open_weather.service.get_closest_history(dt.datetime.now())