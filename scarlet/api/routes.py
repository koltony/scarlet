from fastapi import FastAPI

import scarlet.core.log as log_
import scarlet.api.schemas as schemas
import scarlet.db.models as models
from scarlet.services.arduino_weather import service as arduino_service
from scarlet.services.open_weather import service as open_weather_service
from scarlet.services.irrigation import service as irrigation_service
from scarlet.services.blinds import service as blinds_service

log = log_.service.logger('routes')
app = FastAPI()


class Data:
    def __init__(self):
        self.server_data = {
            '/blinds': {'left_blind': 'nostate', 'right_blind': 'nostate'},
        }


data = Data()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/weather")
async def get_weather():
    return arduino_service.get_weather_data()


@app.post("/weather")
async def post_weather(item: models.ArduinoWeatherData):
    arduino_service.save_weather_data(item)


@app.get("/blinds")
async def get_blinds():
    return blinds_service.get_blinds()


@app.post("/blinds")
async def post_blinds(item: schemas.BlindsPydanticSchema):
    blinds_service.set_blinds(item)


@app.get("/irrigation")
async def get_irrigation():
    return irrigation_service.get_program()


@app.post("/irrigation")
async def post_irrigation(item: schemas.IrrigationPydanticSchema):
    irrigation_service.run_program(item)


@app.get("/open_weather")
async def get_open_weather():
    return open_weather_service.get_weather_data()
