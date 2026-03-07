from contextlib import asynccontextmanager
import argparse
import sys
import os
import asyncio
import schedule
import uvicorn
import paho.mqtt.client as mqtt

sys.path.append(f"/{os.path.join(*__file__.split('/')[:-2])}")

import scarlet.core.log as log_
import scarlet.core.config as config
import scarlet.core.mqtt_module as mqtt_scarlet
import scarlet.db.db
import scarlet.api.routes as routes
import scarlet.services.arduino_weather
import scarlet.services.open_weather
import scarlet.services.blinds
import scarlet.services.irrigation

log = log_.service.logger('main')


def parse_arguments():
    parser = argparse.ArgumentParser(prog='scarlet')
    parser.add_argument('--log_level', required=False, type=str, help="Available logging options are debug, info, warning, error")
    parser.add_argument('--host', required=True, type=str, help="Host of the process")
    parser.add_argument('--port', required=True, type=int, help="Port of the opened server")
    parser.add_argument('--config', required=True, type=str, help="Config yaml path")
    args = parser.parse_args()
    if args.log_level:
        try:
            log_level = getattr(log_.LogLevels, args.log_level.lower())
            log.info(f"log level set to {log_level.value}")
            return log_level
        except AttributeError:
            print(f'Error: {args.log_level} log level does not exists')
    return args


def on_connect(client, userdata, flags, rc):
    log.info(f"Connected with result code: {rc}")

def on_message(client, userdata, msg):
    log.info(f"Received message on {msg.topic}: {msg.payload.decode()}")

mqtt_client = mqtt_scarlet.setup_mqtt(on_connect=on_connect, on_message=on_message)


def build_lifespan(mqtt_host: str):
    @asynccontextmanager
    async def lifespan(app):
        log_.service.change_logger('uvicorn', log_.LogLevels.info)
        log_.service.change_logger('uvicorn.error', log_.LogLevels.info)
        event_loop = asyncio.get_event_loop()
        event_loop.create_task(run_schedule())

        mqtt_client.connect(mqtt_host, 1883, 60)
        mqtt_client.loop_start()

        yield

        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    return lifespan


async def run_schedule():
    schedule.every().monday.at("02:00").do(log_.service.clear_log_file)
    schedule.every().thursday.at("02:00").do(log_.service.clear_log_file)
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)


if __name__ == '__main__':
    log = log_.service.logger('main')
    parser = parse_arguments()
    routes.app.router.lifespan_context = build_lifespan(parser.host)
    log_.service.set_log_level(parser.log_level if parser.log_level else log_.LogLevels.debug)
    config.Process.run_process(config_path=parser.config)

    routes.app.router.lifespan_context = build_lifespan(parser.host)

    uvicorn.run(routes.app, host=parser.host, port=parser.port, loop='uvloop')