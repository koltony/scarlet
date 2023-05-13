import os
import time
import importlib
import traceback
import schedule

import log as log_
import file_encryption
import config
import cache
import open_weather
import arduino_weather
import google_database
import controller


def run():
    path = os.path.dirname(os.path.realpath(__file__))
    config.service.start_process(
        config_file=os.path.join(path, 'config.yaml'),
        encryption_key=os.path.join(path, 'secrets.key'),
        secrets_file=os.path.join(path, 'esecrets.yaml'))
    controller.controller.start_process()


def reload_modules():
    log.info(f"reloading modules")
    importlib.reload(file_encryption)
    importlib.reload(config)
    importlib.reload(cache)
    importlib.reload(open_weather)
    importlib.reload(arduino_weather)
    importlib.reload(google_database)
    importlib.reload(controller)


def cleanup():
    try:
        log.info("Starting cleanup procedures")
        google_database.service.close_connection()
        log.info("removing schedules")
        schedule.clear()
        reload_modules()
    except Exception as e:
        log.error(f"cleanup procedure failed: {traceback.format_exc()}")


if __name__ == '__main__':
    log = log_.service.logger('main')
    log_.service.set_log_level(log_.LogLevels.debug)
    while True:
        try:
            run()
        except Exception as e:
            log.error(f"Critical error: {traceback.format_exc()}")
            cleanup()
            time.sleep(60)

