import datetime as dt
import os
import builtins
import types
import pytest
import polars as pl
import schedule

from unittest.mock import MagicMock, patch

import scarlet.db.models as models
import scarlet.api.schemas as schemas
from scarlet.services.irrigation import IrrigationController


@pytest.fixture
def controller():
    c = IrrigationController(automation = False)
    return c


def make_program(name="prog1", lower=0, upper=10, freq=1, sessions=None):
    prog = models.IrrigationProgram(
        id=1,
        name=name,
        lower_score=lower,
        upper_score=upper,
        frequency=freq,
        is_active=True,
        sessions=sessions or []
    )
    return prog


def make_session(start_time=None):
    return models.IrrigationProgramSession(
        id=1,
        start_time=start_time or dt.datetime(2025, 1, 1, 6, 0).time(),
        zone1=1, zone2=0, zone3=0, zone_connected=True
    )


# def test_schedule_jobs_calls_scheduling_programs_when_automation_true(controller):
#     controller.automation = True
#     with patch.object(controller, "schedule_jobs") as mock_sched:
#         controller.schedule_jobs()
#         mock_sched.assert_called_once()
#         assert any(job.job_func == controller.schedule_jobs for job in schedule.jobs)


def test_calculate_score_returns_zero_if_no_weather():
    with patch("os.path.dirname", return_value=f"/{os.path.join(*__file__.split('/')[:-2])}/scarlet/services"), \
         patch("scarlet.services.open_weather.service.get_history", return_value=[]):
        score = IrrigationController.calculate_score()
        assert score == 0


def test_calculate_score_computes_mean(tmp_path):
    weather_data = [
        types.SimpleNamespace(model_dump=lambda: {
            "timestamp": "2025-01-01T00:00:00",
            "temperature_2m": 20,
            "relative_humidity_2m": 50,
            "wind_speed_10m": 10
        })
    ]
    with patch("os.path.dirname", return_value=f"/{os.path.join(*__file__.split('/')[:-2])}/scarlet/services"), \
         patch("scarlet.services.open_weather.service.get_history", return_value=weather_data):
        score = IrrigationController.calculate_score()
        assert isinstance(score, float)
        assert score > 0
        

def test_run_scheduled_session_skips_if_rain(controller):
    session = make_session()
    with patch("scarlet.services.arduino_weather.service.get_current_weather", return_value=types.SimpleNamespace(rain=1)), \
         patch("scarlet.db.db.service.add") as mock_add:
        controller.run_scheduled_session(session)
        mock_add.assert_not_called()


def test_run_scheduled_session_adds_if_no_rain(controller):
    session = make_session()
    with patch("scarlet.services.arduino_weather.service.get_current_weather", return_value=types.SimpleNamespace(rain=0)), \
         patch("scarlet.db.db.service.add") as mock_add:
        controller.run_scheduled_session(session)
        mock_add.assert_called_once()

def test_set_irrigation_status_does_not_add_when_off(controller):
    session_schema = schemas.IrrigationRunSessionSchema(is_active="off")
    with patch("scarlet.db.db.service.add") as mock_add:
        controller.set_irrigation_status(session_schema)
        mock_add.assert_not_called()


def test_set_automation_false_cancels_jobs(controller):
    controller._scheduled_jobs = [schedule.every().day.do(lambda: None)]
    controller._scheduled_sessions = [schedule.every().day.do(lambda: None)]
    with patch.object(controller, "_self_edit_config") as mock_edit:
        controller.set_automation(False)
        assert controller._scheduled_jobs == []
        assert controller._scheduled_sessions == []
        mock_edit.assert_called_once_with(attribute="automation", new_value=False)
