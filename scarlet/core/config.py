from typing import Any, ClassVar
import yaml
from pydantic import BaseModel
from scarlet.core import log as log_

log = log_.service.logger('config')

class Service:
    services_by_name: dict[str, 'Service'] = dict()
    config: 'Config'
    config_path: ClassVar[str]

    class Config(BaseModel):
        pass

    def __init__(self, name):
        self.services_by_name.update({name: self})

    @classmethod
    def config_services(cls, config: dict[str, Any]):
        for key, value in config.items():
            log.debug(f"configuring {key} service")
            if cls.services_by_name.get(key):
                cls.services_by_name[key].init_config(config=value)
                cls.services_by_name[key].initialize()
                cls.services_by_name[key].schedule_jobs()
            else:
                raise KeyError(f"service {key} does not exists, available: {cls.services_by_name.keys()}")

    def init_config(self, config: dict[str, Any]):
        self.config = self.Config.model_validate(config if config is not None else {})
 
    def initialize(self):
        pass

    def schedule_jobs(self):
        pass


class Controller(BaseModel):
    controller_class_by_class_name: ClassVar[dict[str, 'Service']] = dict()
    controllers_by_class_name: ClassVar[dict[str, 'Service']] = dict()
    config_path: ClassVar[str]


    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.controller_class_by_class_name.update({cls.__name__: cls})

    @classmethod
    def config_controllers(cls, config: dict[str, Any]):
        for key, value in config.items():
            log.debug(f"configuring {key} controller")
            if cls.controller_class_by_class_name.get(key):
                cls.controllers_by_class_name[key] = cls.controller_class_by_class_name[key].model_validate(value if value is not None else {})
                cls.controllers_by_class_name[key].schedule_jobs()
            else:
                raise KeyError(f"controller {key} does not exists, available: {cls.controller_class_by_class_name.keys()}")

    def schedule_jobs(self):
        pass

    def _self_edit_config(self, attribute: str, new_value: Any):
        with open(self.config_path, 'r+') as file:
            data = yaml.safe_load(file)
            data['controllers'][self.__class__.__name__][attribute] = new_value
            file.seek(0)
            yaml.safe_dump(data, file)
            file.truncate()


class Process:
    @staticmethod
    def configure_all(config_path: str, config: dict[str, Any]):
        if config.get('services'):
            Service.config_path = config_path
            Service.config_services(config=config['services'])
        
        if config.get('controllers'):
            Controller.config_path = config_path
            Controller.config_controllers(config=config['controllers'])

    @staticmethod
    def load_yaml(config_path: str) -> dict[str, Any]:
        with open(config_path, 'r') as file:
            data = yaml.safe_load(file)
        return data
    
    @classmethod
    def run_process(cls, config_path):
        config = cls.load_yaml(config_path=config_path)
        cls.configure_all(config_path=config_path, config=config)

