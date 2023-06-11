import os
import schedule
import argparse
import uvicorn
import asyncio

from scarlet.core import log as log_, config
import scarlet.api.routes
import scarlet.services.arduino_weather
import scarlet.services.open_weather
import scarlet.services.blinds
import scarlet.services.irrigation


def parse_arguments():
    parser = argparse.ArgumentParser(prog='scarlet')
    parser.add_argument('--log_level', required=False, type=str, help="Available logging options are debug, info, warning, error")
    args = parser.parse_args()
    if args.log_level:
        try:
            log_level = getattr(log_.LogLevels, args.log_level.lower())
            log.info(f"log level set to {log_level.value}")
            return log_level
        except AttributeError:
            print(f'Error: {args.log_level} log level does not exists')


def run():
    path = os.path.dirname(os.path.realpath(__file__))
    config.service.start_process(
        config_file=os.path.join(path, '..', 'config.yaml'),
        encryption_key=os.path.join(path, '..', 'secrets.key'),
        secrets_file=os.path.join(path, '..', 'esecrets.yaml'))
    uvicorn.run(scarlet.api.routes.app, host="localhost", port=8000, loop='uvloop')


@scarlet.api.routes.app.on_event("startup")
async def startup_event():
    event_loop = asyncio.get_event_loop()
    event_loop.create_task(run_schedule())


async def run_schedule():
    schedule.every().monday.at("02:00").do(log_.service.clear_log_file)
    schedule.every().thursday.at("02:00").do(log_.service.clear_log_file)
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)


if __name__ == '__main__':
    log = log_.service.logger('main')
    log_level = parse_arguments()
    log_.service.set_log_level(log_level if log_level else log_.LogLevels.debug)
    run()

