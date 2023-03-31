import datetime
import time
import config
import mqtt
import cache
import schedule
import open_weather
import arduino_weather
import logging
import controller
import datetime as dt
import log as log_

log = log_.service.logger('main')

log_.service.set_log_level(log_.LogLevels.debug)

c = config.ConfigService()
c.load_config(path='/Users/Tony/PycharmProjects/scarlet/config.yaml')
c.configure_components()
c.initialize_components()


controller.controller.start_process()


