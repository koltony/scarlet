import yaml
from typing import Dict, Optional, Union, TextIO, Any
from enum import Enum
import re
import inspect
import file_encryption
import log as log_

log = log_.service.logger('config')


class ConfigType(Enum):
    string = str
    integer = int
    float = float
    list = list
    dictionary = dict
    secret = str


class ConfigOption:
    def __init__(self, required: bool = False, default: Any = None, *args, **kwargs):
        self.name = None
        self.value = None
        self.default = default
        self.required = required

    @property
    def string(self):
        return lambda config_name, config, component_name: self.process_string(config_name, config, component_name)

    @property
    def integer(self):
        return lambda config_name, config, component_name: self.process_integer(config_name, config, component_name)

    @property
    def float(self):
        return lambda config_name, config, component_name: self.process_float(config_name, config, component_name)

    @property
    def list(self):
        return lambda config_name, config, component_name: self.process_list(config_name, config, component_name)

    @property
    def dictionary(self):
        return lambda config_name, config, component_name: self.process_dictionary(config_name, config, component_name)

    @property
    def secret(self):
        return lambda config_name, config, component_name: self.process_secret(config_name, config, component_name)

    def process(self, config_type, config_name, config, component_name) -> Any:
        log.debug(f"passed value for {config_name}: {config}")
        if config is not None:
            if not isinstance(config, config_type.value):
                raise TypeError(f"{component_name}.{config_name} should be a(n) {config_type.value}, got: {type(config)}")
            return config

        if not self.required:
            return self.default

        # seems like lambda functions eats errors in some situations
        raise TypeError(f"{component_name}.{config_name} is not configured")

    def process_string(self, config_name, config, component_name) -> str:
        return self.process(ConfigType.string, config_name, config, component_name)

    def process_integer(self, config_name, config, component_name) -> int:
        return self.process(ConfigType.integer, config_name, config, component_name)

    def process_float(self, config_name, config, component_name) -> float:
        return self.process(ConfigType.float, config_name, config, component_name)

    def process_list(self, config_name, config, component_name) -> list:
        return self.process(ConfigType.list, config_name, config, component_name)

    def process_dictionary(self, config_name, config, component_name) -> dict:
        return self.process(ConfigType.dictionary, config_name, config, component_name)

    @staticmethod
    def process_secret(config_name, config, component_name):
        log.debug(f"configure secret value for {config_name}: {config}")
        secrets = yaml.safe_load(service.secrets)
        if config is not None:
            for name, value in secrets.items():
                if name == config:
                    return value

        raise ValueError(f"{component_name}.{config_name} is not configured")


class ConfigService:

    def __init__(self):
        self.config_file = None
        self.secrets = None
        self.config_classes = self._collect_config_classes()

    def clear_all(self):
        self.config_file = None
        self.secrets = None
        self.config_classes = self._collect_config_classes()
        Component.component_classes_by_name = dict()

    def load_secrets(self, encryption_key: str, encrypted_file: str):
        log.debug(f"loading secrets file")
        self.secrets = file_encryption.Secrets.decrypt_file(encryption_key=encryption_key, encrypted_file=encrypted_file)

    def _load_yaml_from_raw(self, stream: Union[str, TextIO]):
        try:
            self.config_file = yaml.load(stream, Loader=yaml.FullLoader)
        except yaml.YAMLError as exc:
            log.error(exc)

    def _load_yaml_from_file(self, path):
        log.debug(f"loading config file from: {path}")
        with open(path, "r") as stream:
            self._load_yaml_from_raw(stream)

    def load_config(self, path: str = None, raw_yaml: str = None):
        if (path and raw_yaml) or (not path and not raw_yaml):
            raise ValueError(f"path or raw_yaml have to be specified but not both")

        if path:
            self._load_yaml_from_file(path)
        else:
            self._load_yaml_from_raw(raw_yaml)

    @staticmethod
    def _collect_config_classes():
        config_option_types = ['ConfigOption']
        for config_class in ConfigOption.__subclasses__():
            config_option_types.append(config_class.__class__.__name__)
        return config_option_types

    def _is_config_option(self, member) -> bool:
        for config_class in self.config_classes:
            if inspect.isfunction(member) and re.findall(r"<function\s+{}\.[a-zA-Z0-9]+\.<locals>\.<lambda>".format(re.escape(config_class)), str(member)):
                return True
        return False

    def _get_configureables_for_component(self, component) -> list:
        members = inspect.getmembers(component)
        return [member[0] for member in members if self._is_config_option(member[1])]

    @staticmethod
    def _set_configure_defaults_for_component(component, not_configured_attributes: list):
        log.info(f"trying defaults for {component.name} attributes: {not_configured_attributes} ")
        for config_name in not_configured_attributes:
            setattr(component, config_name, getattr(component, config_name)(config_name, None, component.name))

    def configure_component(self, component, config):
        configureables = self._get_configureables_for_component(component)
        log.info(f"configurable attributes of {component.name}: {configureables}")
        for config_name, config in config.items():
            if hasattr(component, config_name):
                if config_name in Component.component_classes_by_name.keys():
                    self.configure_component(Component.component_classes_by_name[config_name], config)
                elif config_name in configureables:
                    log.debug(f'configuring {component.name}.{config_name}')
                    setattr(component, config_name, getattr(component, config_name)(config_name, config, component.name))
                    configureables.remove(config_name)
                else:
                    ValueError(f"{component.name}.{config_name} is not configurable")
            else:
                ValueError(f'{component} does not have attribute: {config_name}')
        if configureables:
            self._set_configure_defaults_for_component(component, configureables)

    def configure_components(self):
        for key, config in self.config_file.items():
            log.info(f'configuring component: {key}')
            component = Component.component_classes_by_name.get(key)
            if component:
                self.configure_component(component, config)
            else:
                ValueError(f'component: {key} does not exist')

    @staticmethod
    def initialize_components():
        for name, component in Component.component_classes_by_name.items():
            if hasattr(component, 'initialize'):
                log.info(f'Initializing component: {name}')
                component.initialize()
            else:
                log.debug(f'Component {name} does not need to be initialied')
        log.info("All components have been initialized")

    def start_process(self, config_file: str, encryption_key: Optional[str] = None, secrets_file: Optional[str] = None):
        if secrets_file and encryption_key:
            self.load_secrets(encryption_key=encryption_key, encrypted_file=secrets_file)

        self.load_config(config_file)
        self.configure_components()
        self.initialize_components()


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
