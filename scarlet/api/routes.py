import os
import datetime as dt

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import asyncio

import scarlet.core.log as log_
import scarlet.api.schemas as schemas
import scarlet.db.models as models
from scarlet.core.config import Controller
from scarlet.services.arduino_weather import service as arduino_service
from scarlet.services.open_weather import service as open_weather_service

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

log = log_.service.logger('routes')
app = FastAPI()



app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "..", "static")),name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "..", "templates"))


@app.get("/", response_class=HTMLResponse)
@app.get("/irrigation/ui", response_class=HTMLResponse)
def irrigation_page(request: Request):
    return templates.TemplateResponse("irrigation.html", {"request": request})


@app.get("/blinds/ui", response_class=HTMLResponse)
def blinds_page(request: Request):
    return templates.TemplateResponse("blinds.html", {"request": request})


# Simple in-memory rooms store for frontend development / dummy data
_next_room_id = 3
ROOMS = [
    {"id": 1, "name": "Living Room", "temperature": 21.4, "humidity": 44, "devices": [
        {"id": 1, "type": "sonoff-sensor", "name": "LR Sensor", "temperature": 21.4, "humidity": 44, "battery": 97},
        {"id": 2, "type": "sonoff-valve", "name": "LR Valve", "battery": 98}
    ], "schedule": [{"time": "06:30", "temp": 20}, {"time": "22:00", "temp": 16}]},
    {"id": 2, "name": "Bedroom", "temperature": 19.1, "humidity": 48, "devices": [], "schedule": []}
]


@app.get("/rooms/ui", response_class=HTMLResponse)
def rooms_page(request: Request):
    return templates.TemplateResponse("rooms.html", {"request": request})


@app.get("/api/rooms")
def api_get_rooms():
    # Return summary list
    return [{"id": r["id"], "name": r["name"], "temperature": r.get("temperature"), "humidity": r.get("humidity")} for r in ROOMS]


@app.post("/api/rooms")
async def api_create_room(item: dict):
    global _next_room_id
    name = item.get('name', 'New Room')
    room = {"id": _next_room_id, "name": name, "temperature": None, "humidity": None, "devices": [], "schedule": []}
    _next_room_id += 1
    ROOMS.append(room)
    return room


@app.post("/api/rooms/{room_id}/delete")
async def api_delete_room(room_id: int):
    global ROOMS
    ROOMS = [r for r in ROOMS if r['id'] != room_id]
    return {"detail": "deleted"}


@app.get("/api/rooms/{room_id}")
def api_get_room(room_id: int):
    room = next((r for r in ROOMS if r['id'] == room_id), None)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@app.post("/api/rooms/{room_id}/devices")
async def api_add_device(room_id: int, item: dict):
    room = next((r for r in ROOMS if r['id'] == room_id), None)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    dev_id = 1
    if room['devices']:
        dev_id = max(d['id'] for d in room['devices']) + 1
    dev = {"id": dev_id, "type": item.get('type'), "name": item.get('name', item.get('type')), "temperature": item.get('temperature'), "humidity": item.get('humidity'), "battery": item.get('battery')}
    room['devices'].append(dev)
    return dev


@app.post("/api/rooms/{room_id}/devices/{device_id}/delete")
async def api_remove_device(room_id: int, device_id: int):
    room = next((r for r in ROOMS if r['id'] == room_id), None)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    room['devices'] = [d for d in room['devices'] if d['id'] != device_id]
    return {"detail": "deleted"}


@app.post("/api/rooms/{room_id}/schedule")
async def api_add_schedule(room_id: int, item: dict):
    room = next((r for r in ROOMS if r['id'] == room_id), None)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    entry = {"time": item.get('time'), "temp": item.get('temp')}
    room['schedule'].append(entry)
    return entry



@app.get("/weather")
async def get_weather():
    return arduino_service.get_current_weather()


@app.get("/weather/history")
async def get_historic_weather():
    return arduino_service.get_history(dt.datetime.now())


@app.post("/blinds")
async def post_blinds(item: schemas.BlindsPydanticSchema):
    status = Controller.controllers_by_class_name['BlindsController'].set_blinds(item)
    if status is True:
        log.info('arduino accepted the request')
        return {"detail": "Accepted"}
    else:
        log.warning('arduino (blinds) not responded the request')
        return {"detail": "No response"}


@app.post("/irrigation")
async def post_irrigation(item: schemas.IrrigationRunSessionSchema):
    status = Controller.controllers_by_class_name['IrrigationController'].run_session(item)
    if status is True:
        log.info('arduino accepted the request')
        return {"detail": "Accepted"}
    else:
        log.warning('arduino (irrigation) not responded the request')
        return {"detail": "No response"}

@app.get("/open_weather")
async def get_open_weather():
    return open_weather_service.get_current_data()


@app.get("/open_weather/score")
async def get_irrigation_score():
    return Controller.controllers_by_class_name['IrrigationController'].calculate_score()


@app.post("/irrigation/automation")
async def post_irrigation_automation(item: schemas.AutomationState):
    Controller.controllers_by_class_name['IrrigationController'].set_automation(item.automation)


@app.get("/irrigation/automation")
async def get_irrigation_automation():
    return {"automation": Controller.controllers_by_class_name['IrrigationController'].automation}


@app.post("/blinds/automation")
async def post_blinds_automation(item: schemas.AutomationState):
    Controller.controllers_by_class_name['BlindsController'].set_automation(item.automation)


@app.get("/blinds/automation")
async def get_blinds_automation():
    return {"automation": Controller.controllers_by_class_name['BlindsController'].automation}


@app.post("/blinds/light_limit")
async def post_blinds_light_limit(item: schemas.BlindsSettingLightLimitSchema):
    Controller.controllers_by_class_name['BlindsController'].light_limit = item.limit


@app.get("/blinds/light_limit")
async def get_blinds_light_limit():
    return {"automation": Controller.controllers_by_class_name['BlindsController'].light_limit}


@app.post("/irrigation/program")
async def post_irrigation_program(item: schemas.IrrigationCreateProgramSchema):
    """Adds a program with defined session to the database"""
    dict_ = item.model_dump()
    program = models.IrrigationProgram.model_validate(dict_)
    program.sessions = [models.IrrigationProgramSession(**d) for d in dict_['sessions']]
    Controller.controllers_by_class_name['IrrigationController'].set_irrigation_program(program)


@app.post("/irrigation/program/{program_id}/session/create")
async def post_irrigation_session(program_id: int, item: schemas.IrrigationCreateProgramSessionSchema):
    """Adds a program with defined session to the database"""
    program = Controller.controllers_by_class_name['IrrigationController'].get_irrigation_program_by_id(program_id)
    program.sessions = program.sessions + [models.IrrigationProgramSession(**item.model_dump())]
    Controller.controllers_by_class_name['IrrigationController'].update_irrigation_program(program)


@app.get("/irrigation/sessions/history", response_model=list[schemas.HistoricalIrrigationRunSessionSchema])
async def get_historical_sessions():
    sessions = list()
    for session in Controller.controllers_by_class_name['IrrigationController'].get_historical_sessions():
        session_dict =  session.model_dump()
        session_dict.update({'is_active': "on"})
        sessions.append(session_dict)
    return sessions


@app.get("/irrigation/program/all", response_model=list[schemas.IrrigationGetProgramSchema])
async def get_irrigation_programs():
    """Retreives all programs with it's sessions"""
    return Controller.controllers_by_class_name['IrrigationController'].get_irrigation_programs()


@app.get("/irrigation/program/{program_id}", response_model=schemas.IrrigationGetProgramSchema)
async def get_irrigation_program(program_id: int):
    program = Controller.controllers_by_class_name['IrrigationController'].get_irrigation_program_by_id(program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    return program


@app.patch("/irrigation/program/{program_id}", response_model=schemas.IrrigationUpdateProgramSchema)
async def update_irrigation_program(program_id: int, update: schemas.IrrigationUpdateProgramSchema):
    """
    Updates a program based on filled out parts of the schema
    Notes:
        Sessions are updated separately
    """
    program = Controller.controllers_by_class_name['IrrigationController'].get_irrigation_program_by_id(program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    for key, value in update.model_dump(exclude_none=True).items():
        if key != 'sessions':
            setattr(program, key, value)

    Controller.controllers_by_class_name['IrrigationController'].update_irrigation_program(program)
    return program


@app.post("/irrigation/program/{program_id}/delete")
async def delete_irrigation_program(program_id: int):
    """
    Deletes program
    """
    program = Controller.controllers_by_class_name['IrrigationController'].get_irrigation_program_by_id(program_id)
    [Controller.controllers_by_class_name['IrrigationController'].delete_irrigation_session_by_id(session.id) for session in program.sessions]
    Controller.controllers_by_class_name['IrrigationController'].delete_irrigation_program_by_id(program_id)


@app.post("/irrigation/program/{program_id}/session/{session_id}/delete")
async def delete_session(program_id: int, session_id: int):
    """
    Deletes a session from a program
    """
    program = Controller.controllers_by_class_name['IrrigationController'].get_irrigation_program_by_id(program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    # Find the session
    session = next((s for s in program.sessions if s.id == session_id), None)
    if not session:
        raise HTTPException(status_code=404, detail="Session for program not found")

    # Remove it
    program.sessions = [s for s in program.sessions if s.id != session_id]
    Controller.controllers_by_class_name['IrrigationController'].update_irrigation_program(program)
    Controller.controllers_by_class_name['IrrigationController'].delete_irrigation_session_by_id(session_id)
    return {"detail": "Session deleted"}


@app.patch("/irrigation/program/session/{session_id}")
async def update_session(session_id: int, update: schemas.IrrigationUpdateProgramSessionSchema):
    """Updates a session based on filled out parts of the schema"""
    session = Controller.controllers_by_class_name['IrrigationController'].get_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    for key, value in update.model_dump(exclude_none=True).items():
        setattr(session, key, value)

    Controller.controllers_by_class_name['IrrigationController'].update_irrigation_session(session)
    return session
