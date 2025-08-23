from contextlib import asynccontextmanager
import argparse
import sys
import os
import asyncio
import schedule
import uvicorn

# sys.path.append(f"/{os.path.join(*__file__.split('/')[:-2])}")

import scarlet.core.log as log_
import scarlet.core.config as config
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


@asynccontextmanager
async def lifespan(app):
    log_.service.change_logger('uvicorn', log_.LogLevels.info)
    log_.service.change_logger('uvicorn.error', log_.LogLevels.info)
    event_loop = asyncio.get_event_loop()
    event_loop.create_task(run_schedule())
    yield


routes.app.router.lifespan_context = lifespan


async def run_schedule():
    schedule.every().monday.at("02:00").do(log_.service.clear_log_file)
    schedule.every().thursday.at("02:00").do(log_.service.clear_log_file)
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)


def run():
    uvicorn.run(routes.app, host="localhost", port=8000, loop='uvloop')


if __name__ == '__main__':
    log = log_.service.logger('main')
    parser = parse_arguments()
    log_.service.set_log_level(parser.log_level if parser.log_level else log_.LogLevels.debug)
    config.Process.run_process(config_path=parser.config)
    run()
