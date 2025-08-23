from typing import Callable, Any
import os
import pytest
import pytest_assume
import yaml
from scarlet.core import config


class DummyController(config.Controller):
    variable1: int
    variable2: str


class DummyService(config.Service):
    class Config(config.Service.Config):
        variable1: int
        variable2: str

service = DummyService('dummy_service')

@pytest.mark.parametrize("cfg, results_by_location, raise_error", [
    (
        {
            "services": {
                'dummy_service': {
                    'variable1': 123,
                    'variable2': 'hello'
                }
            }
        },
        [
            (lambda c: c['services']['dummy_service']['variable1'], 123),
            (lambda c: c['services']['dummy_service']['variable2'], 'hello')
        ],
        None
    ),
    (
        {
            "services": {
                'not_existing_dummy_service': {
                    'variable1': 123,
                    'variable2': 'hello'
                }
            }
        },
        [],
        KeyError
    )
])
def test_service_config(cfg: dict, results_by_location: tuple[Callable, Any], raise_error: Exception | None):
    if raise_error is None:
        config.Service.config_services(cfg['services'])
        for result in results_by_location:
            pytest.assume(result[0](cfg) == result[1])
    else:
        with pytest.raises(raise_error):
            config.Service.config_services(cfg['services'])


@pytest.mark.parametrize("cfg, results_by_location, raise_error", [
    (
        {
            "controllers": {
                'DummyController': {
                    'variable1': 123,
                    'variable2': 'hello'
                }
            }
        },
        [
            (lambda c: c['controllers']['DummyController']['variable1'], 123),
            (lambda c: c['controllers']['DummyController']['variable2'], 'hello')
        ],
        None
    ),
    (
        {
            "controllers": {
                'NotExistingDummyController': {
                    'variable1': 123,
                    'variable2': 'hello'
                }
            }
        },
        [],
        KeyError
    )
])
def test_controller_config(cfg: dict, results_by_location: tuple[Callable, Any], raise_error: Exception | None):
    if raise_error is None:
        config.Controller.config_controllers(cfg['controllers'])
        for result in results_by_location:
            pytest.assume(result[0](cfg) == result[1])
    else:
        with pytest.raises(raise_error):
            config.Controller.config_controllers(cfg['controllers'])


@pytest.mark.parametrize("cfg", [
      { 
          "services": {
                'dummy_service': {
                    'variable1': 123,
                    'variable2': 'hello'
                }
            },
            "controllers": {
                'DummyController': {
                    'variable1': 123,
                    'variable2': 'hello'
                }
            }
        },
])

def test_process_integration(test_resource_dir, cfg: str):
    path = os.path.join(test_resource_dir, 'test_config.yaml')
    with open(path, 'w') as file:
        yaml.dump(cfg, file)

    config.Process.run_process(path)
    