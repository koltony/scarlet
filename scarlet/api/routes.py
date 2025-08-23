import os

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

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


@app.get("/weather")
async def get_weather():
    return arduino_service.get_current_weather()


@app.post("/weather")
async def post_weather(item: models.ArduinoWeatherData):
    arduino_service.append_weather_data(item)


@app.get("/blinds")
async def get_blinds():
    return Controller.controllers_by_class_name['BlindsController'].get_blinds()


@app.post("/blinds")
async def post_blinds(item: schemas.BlindsPydanticSchema):
    Controller.controllers_by_class_name['BlindsController'].set_blinds(item)


@app.get("/irrigation")
async def get_irrigation():
    return Controller.controllers_by_class_name['IrrigationController'].get_program()


@app.post("/irrigation")
async def post_irrigation(item: schemas.IrrigationPydanticSchema):
    Controller.controllers_by_class_name['IrrigationController'].run_program(item)


@app.get("/open_weather")
async def get_open_weather():
    return open_weather_service.get_current_data()


@app.post("/irrigation/automation")
async def post_irrigation_automation(item: bool):
    Controller.controllers_by_class_name['IrrigationController'].set_automation(item)


@app.post("/blinds/automation")
async def post_blinds_automation(item: bool):
    Controller.controllers_by_class_name['BlindsController'].set_automation(item)


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
