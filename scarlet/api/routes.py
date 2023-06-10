from fastapi import FastAPI
import scarlet.api.schemas as schemas
from scarlet.services.arduino_weather import service as arduino_service
from scarlet.services.open_weather import service as open_weather_service

app = FastAPI()


class Data:
    def __init__(self):
        self.server_data = {
            '/weather': {'wind': 0, 'light': 0, 'rain': 0},
            '/blinds': {'left_blind': 'nostate', 'right_blind': 'nostate'},
            '/irrigation': {'zone1': 0, 'zone2': 0, 'zone3': 0, 'zone_connected': 0, 'active': 'off'}
        }


data = Data()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/weather")
async def get_weather():
    return arduino_service.get_last_data()


@app.post("/weather")
async def post_weather(item: schemas.ArduinoWeatherPydanticSchema):
    arduino_service.save_weather_data(item)


@app.get("/blinds")
async def get_blinds():
    return data.server_data["/blinds"]


@app.post("/blinds")
async def post_blinds(item: schemas.BlindsPydanticSchema):
    item_dict = item.dict()
    for name, value in item_dict.items():
        data.server_data["/blinds"][name] = value


@app.get("/irrigation")
async def get_irrigation():
    return data.server_data["/irrigation"]


@app.post("/irrigation")
async def post_irrigation(item: schemas.IrrigationPydanticSchema):
    item_dict = item.dict()
    for name, value in item_dict.items():
        data.server_data["/irrigation"][name] = value


@app.get("/open_weather")
async def get_open_weather():
    return open_weather_service.get_weather_data()
