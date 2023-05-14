import pytest
from enum import Enum
import importlib
import textwrap
import scarlet
from scarlet import config
from scarlet import log as log_

log = log_.service.logger('test_config')


class DummyNoConfigComponent(config.Component):
    def __init__(self, name):
        super().__init__(name)
        self.dummy_attribute = 1


class DummySubComponent(config.Component):
    def __init__(self, name):
        super().__init__(name)

        self.dummy_string = config.ConfigOption(required=True).string
        self.dummy_integer = config.ConfigOption(required=True).integer
        self.dummy_float = config.ConfigOption(required=True).float
        self.dummy_list = config.ConfigOption(required=True).list
        self.dummy_dictionary = config.ConfigOption(required=True).dictionary

    def __repr__(self):
        return f"{self.__class__.__name__}(" \
                   f"dummy_string={self.dummy_string}," \
                   f" dummy_integer={self.dummy_integer}," \
                   f" dummy_float={self.dummy_float}," \
                   f" dummy_list={self.dummy_integer}," \
                   f" dummy_dictionary={self.dummy_dictionary})"


class DummyComponent(config.Component):
    def __init__(self, name):
        super().__init__(name)
        self.DummySubComponent = DummySubComponent('DummySubComponent')
        self.dummy_string = config.ConfigOption(required=True).string
        self.dummy_integer = config.ConfigOption(required=True).integer
        self.dummy_float = config.ConfigOption(required=True).float
        self.dummy_list = config.ConfigOption(required=True).list
        self.dummy_dictionary = config.ConfigOption(required=True).dictionary


config_options = textwrap.dedent("""\
    SubComponent:
      dummy_string: {dummy_string}
      dummy_integer: {dummy_integer}
      dummy_float: {dummy_float}
      dummy_list: {dummy_list}
      dummy_dictionary: {dummy_dictionary}

""")


def load_config(config_file, dummy_string, dummy_integer, dummy_float, dummy_list, dummy_dictionary):
    formatted_config_options = config_options.format(
        dummy_string=dummy_string,
        dummy_integer=dummy_integer,
        dummy_float=dummy_float,
        dummy_list=dummy_list,
        dummy_dictionary=dummy_dictionary
    )
    log.info(formatted_config_options)
    config.service.load_config(raw_yaml=formatted_config_options)


@pytest.mark.parametrize("dummy_string, dummy_integer, dummy_float, dummy_list, dummy_dictionary", [
     (1237171, 1, 1.2, ['hello'], {'hello': 1}),
     ('hello', 'h', 1.2, ['hello'], {'hello': 1}),
     ('hello', 1, 'h', ['hello'], {'hello': 1}),
     ('hello', 1, 1.2, {'hello': 1}, {'hello': 1}),
     ('hello', 1, 1.2, ['hello'], ['hello'])])
def test_config_option_validation(dummy_string, dummy_integer, dummy_float, dummy_list, dummy_dictionary):
    config.service.clear_all()
    component = DummySubComponent('SubComponent')
    load_config(config_options, dummy_string, dummy_integer, dummy_float, dummy_list, dummy_dictionary)
    with pytest.raises(TypeError):
        config.service.configure_components()


@pytest.mark.parametrize("dummy_string, dummy_integer, dummy_float, dummy_list, dummy_dictionary", [
    ('hello', 1, 1.2, ['hello'], {'hello': 1})])
def test_config_option_in_component(dummy_string, dummy_integer, dummy_float, dummy_list, dummy_dictionary):
    config.service.clear_all()
    component = DummySubComponent('SubComponent')
    load_config(config_options, dummy_string, dummy_integer, dummy_float, dummy_list, dummy_dictionary)
    config.service.configure_components()
    config.service.initialize_components()

    assert \
        (component.dummy_string == dummy_string) and \
        (component.dummy_integer == dummy_integer) and \
        (component.dummy_float == dummy_float) and \
        (component.dummy_list == dummy_list) and \
        (component.dummy_dictionary == dummy_dictionary)
