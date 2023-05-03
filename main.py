import datetime
import time
import config
import file_encryption
import cache
import schedule
import open_weather
import arduino_weather
import logging
import controller
import google_database
import datetime as dt
import random
import log as log_


def run():
    log = log_.service.logger('main')

    log_.service.set_log_level(log_.LogLevels.debug)

    config.service.start_process(config_file='config.yaml', encryption_key='secrets.key', secrets_file='esecrets.yaml')
    controller.controller.start_process()


if __name__ == '__main__':
    run()
