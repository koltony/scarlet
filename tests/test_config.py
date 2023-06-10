import pytest
import textwrap
from scarlet.core import log as log_, config

log = log_.service.logger('test_config')


class DummyNoConfigComponent(config.Component):
    def __init__(self, name):
        super().__init__(name)
        self.dummy_attribute = 1


class DummySubComponent(config.Component):
    def __init__(self, name):
        super().__init__(name)

        self.dummy_string = config.ConfigOption(required=True).string
        self.dummy_integer = config.ConfigOption(required=False, default=999).integer
        self.dummy_float = config.ConfigOption(required=True).float
        self.dummy_list = config.ConfigOption(required=True).list
        self.dummy_dictionary = config.ConfigOption(required=True).dictionary

    def __repr__(self):
        return f"{self.__class__.__name__}(" \
                   f"name = {self.name}"\
                   f"dummy_string={self.dummy_string}," \
                   f" dummy_integer={self.dummy_integer}," \
                   f" dummy_float={self.dummy_float}," \
                   f" dummy_list={self.dummy_integer}," \
                   f" dummy_dictionary={self.dummy_dictionary})"


class DummyMainComponent(config.Component):
    def __init__(self, name):
        super().__init__(name)
        self.DummySubComponent = DummySubComponent('DummySubComponent')

    def __repr__(self):
        return f"{self.__class__.__name__}(" \
                   f"name = {self.name}, "\
                   f"DummySubComponent={self.DummySubComponent})"


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

    assert \
        (component.dummy_string == dummy_string) and \
        (component.dummy_integer == dummy_integer) and \
        (component.dummy_float == dummy_float) and \
        (component.dummy_list == dummy_list) and \
        (component.dummy_dictionary == dummy_dictionary)


missing_config_options = textwrap.dedent("""\
    SubComponent:
      dummy_string: {dummy_string}
    """)


def test_required_configs():
    config.service.clear_all()
    component = DummySubComponent('SubComponent')
    config.service.load_config(raw_yaml=missing_config_options)
    with pytest.raises(TypeError):
        config.service.configure_components()


only_required_config_options = textwrap.dedent("""\
    SubComponent:
      dummy_string: Hello
      dummy_float: 1.2
      dummy_list: ['hello']
      dummy_dictionary: {'hello': 1}
    """)


def test_default_configs():
    config.service.clear_all()
    component = DummySubComponent('SubComponent')
    config.service.load_config(raw_yaml=only_required_config_options)
    config.service.configure_components()
    assert component.dummy_integer == 999


sub_component_config_options = textwrap.dedent("""\
    MainComponent:
      DummySubComponent:
        dummy_string: HelloSub
        dummy_float: 1.2
        dummy_list: ['hello']
        dummy_dictionary: {'hello': 1}
    """)


def test_sub_component():
    config.service.clear_all()
    component = DummyMainComponent('MainComponent')
    config.service.load_config(raw_yaml=sub_component_config_options)
    config.service.configure_components()
    assert component.DummySubComponent.dummy_string == 'HelloSub'

