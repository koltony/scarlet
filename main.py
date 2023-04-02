import datetime
import time
import config
import mqtt
import file_encryption
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

config.service.start_process(config_file='config.yaml', encryption_key='testkey.key', secrets_file='esecrets.yaml')
controller.controller.start_process()



