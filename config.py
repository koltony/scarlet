import yaml
from typing import Dict, List, Optional, Any
import log as log_
import inspect

log = log_.service.logger('config')


class ConfigOption:
    def __init__(self, required: bool = False, default: Any = None):
        self.name = None
        self.bounded_component = None
        self.value = None
        self.default = default
        self.required = required

    def process(self, config_name, bounded_component) -> Any:
        if self.required:
            if self.value is None:
                ValueError(f"{bounded_component} configuration is missing for {config_name}")

        if self.value:
            return self.value
        else:
            return self.default


class ConfigService:

    def __init__(self):
        self.config_file = None

    def load_config(self, path: str):
        with open(path, "r") as stream:
            try:
                self.config_file = yaml.safe_load(stream)
                log.debug(f"loading config file from: {path}")
            except yaml.YAMLError as exc:
                log.error(exc)

    def configure_component(self, component, config):
        log.info(config)
        for config_name, config in config.items():
            if hasattr(component, config_name):
                if config_name in Component.component_classes_by_name.keys():
                    self.configure_component(Component.component_classes_by_name[config_name], config)
                else:
                    log.debug(f'configuring {component.name}.{config_name}')
                    setattr(component, config_name, config)
            else:
                log.warning(f'{component} does not have attribute: {config_name}')

    def configure_components(self):
        for key, config in self.config_file.items():
            log.debug(f'Configuring component: {key}')
            component = Component.component_classes_by_name.get(key)
            if component:
                self.configure_component(component, config)
            else:
                ValueError(f'Component: {key} does not exist')

    @staticmethod
    def initialize_components():
        for name, component in Component.component_classes_by_name.items():
            if hasattr(component, 'initialize'):
                log.info(f'Initializing component: {name}')
                component.initialize()
            else:
                log.debug(f'Component {name} does not need to be initialied')
        log.info("All components have been initialized")


class Component:

    component_classes_by_name = dict()  # type: Dict[str, Component]

    def __init__(self, name: str):
        self.name = name
        self._register_component(name)

    def _register_component(self, name: str):
        log.debug(f'registering component: {name}')
        if self.component_classes_by_name.get(name) is None:
            self.component_classes_by_name.update({name: self})
        ValueError(f"Component with name {name} already exists")


service = ConfigService()