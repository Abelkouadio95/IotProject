from typing import Annotated
from fastapi import Depends, FastAPI, Form, Path, Query, Request, Response, WebSocket, WebSocketDisconnect, WebSocketException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import ValidationError
from sqlmodel import select
from iot_proj.deps import get_doctor, get_patient
from iot_proj.doctor_services import create_doctor, get_doc_conversation_entries, get_doc_convos, get_doctor as get_doc_login, get_doctor_by_id
from iot_proj.form_models import (
    CreateConvo,
    DoctorLoginFormData,
    DoctorM,
    DoctorRegisterModel,
    PatientLoginFormData,
    PatientM,
    PatientRegisterFormdata,
    WebsocketRelayMessage,
)
from iot_proj.models import Conversation, ConversationEntries, SessionDep, create_db_and_tables
import logging

from iot_proj.user_services import Error, create_patient, create_u_convos, get_conversation_entries, get_user, get_user_convos
from iot_proj.websoc import ConnectionManager


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="templates")
app = FastAPI()
ws_connection_manager = ConnectionManager()

@app.on_event("startup")
def on_startup():
    create_db_and_tables()


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, name="index.html", context={})


@app.get("/register", response_class=HTMLResponse)
def register_patient(request: Request):
    return templates.TemplateResponse(
        request, name="patients/auth/register.html", context={}
    )


@app.post("/register", response_class=RedirectResponse)
def register_patient_post(
    request: Request,
    formdata: Annotated[PatientRegisterFormdata, Form()],
    session: SessionDep,
):
    result = create_patient(formdata, session)
    if isinstance(result, Error):
        return templates.TemplateResponse(
            request,
            name="patients/auth/register.html",
            status_code=status.HTTP_400_BAD_REQUEST,
            context={"form": formdata, "error": result.error},
        )
    response = RedirectResponse(
        url=request.url_for("patient_home"), status_code=status.HTTP_302_FOUND
    )
    response.set_cookie("userid", result.id)
    return response


@app.get("/login")
def patient_login(request: Request):
    return templates.TemplateResponse(request, name="patients/auth/login.html")


@app.post("/login", response_class=RedirectResponse)
def patient_login_post(
    request: Request,
    formdata: Annotated[PatientLoginFormData, Form()],
    session: SessionDep,
):
    result = get_user(formdata, session)
    if isinstance(result, Error):
        return templates.TemplateResponse(
            request,
            name="patients/auth/login.html",
            status_code=status.HTTP_400_BAD_REQUEST,
            context={"form": formdata, "error": result.error},
        )
    response = RedirectResponse(
        url=request.url_for("patient_home"), status_code=status.HTTP_302_FOUND
    )
    response.set_cookie("userid", result.id)
    return response


PatientDep = Annotated[PatientM | RedirectResponse, Depends(get_patient)]


@app.get("/patient/home", response_class=HTMLResponse)
def patient_home(request: Request, user: PatientDep):
    if isinstance(user, RedirectResponse):
        return user
    return templates.TemplateResponse(
        request, name="patients/home.html", context={"user": user}
    )


@app.get("/doctor/register", response_class=HTMLResponse)
def doctor_register(request: Request):
    return templates.TemplateResponse(request, name="doctor/auth/register.html")


@app.post("/doctor/register", response_class=RedirectResponse)
def doctor_register_post(
    request: Request,
    formdata: Annotated[DoctorRegisterModel, Form()],
    session: SessionDep,
):
    result = create_doctor(formdata, session)
    if isinstance(result, Error):
        return templates.TemplateResponse(
            request,
            name="doctor/auth/register.html",
            context={"form": formdata, "error": result.error},
        )
    response = RedirectResponse(
        url=request.url_for("doctor_home"), status_code=status.HTTP_302_FOUND
    )
    response.set_cookie("docid", result.id)
    return response


DoctorDep = Annotated[DoctorM | RedirectResponse, Depends(get_doctor)]


@app.get("/doctor/login", response_class=HTMLResponse)
def doctor_login(request: Request):
    return templates.TemplateResponse(request, name="doctor/auth/login.html")

@app.post("/doctor/login", response_class=RedirectResponse)
def doctor_login_post(request: Request, formdata: Annotated[DoctorLoginFormData, Form()], session: SessionDep):
    result = get_doc_login(formdata, session)
    if isinstance(result, Error):
        return templates.TemplateResponse(
            request,
            name="patients/auth/login.html",
            status_code=status.HTTP_400_BAD_REQUEST,
            context={"form": formdata, "error": result.error}
        )
    response = RedirectResponse(
        url=request.url_for("doctor_home"),
        status_code=status.HTTP_302_FOUND,
    )
    response.set_cookie("docid", result.id)
    return response


@app.get("/doctor/home", response_class=HTMLResponse)
def doctor_home(request: Request, user: DoctorDep):
    if isinstance(user, RedirectResponse):
        return user
    return templates.TemplateResponse(
        request, name="doctor/home.html", context={"user": user}
    )

@app.get("/get/doctor/{id}")
def get_doc_by_id(id: Annotated[str, Path()], session: SessionDep):
    doc = get_doctor_by_id(id, session)
    if isinstance(doc, Error):
        return JSONResponse(content={"error": doc.error}, status_code=status.HTTP_400_BAD_REQUEST)
    return doc.model_dump_json()

@app.get("/patient/conversation")
def get_convo_pat(user: PatientDep, session: SessionDep):
    if isinstance(user, RedirectResponse):
        return user
    convos = get_user_convos(user.id, session)
    return {"conversations": convos}

@app.get("/doctor/conversation")
def get_convo_doc(user: DoctorDep, session: SessionDep):
    if isinstance(user, RedirectResponse):
        return user
    convos = get_doc_convos(user.id, session)
    return {"conversations": convos}

@app.post("/patient/conversation")
def create_convo_pat(user: PatientDep, session: SessionDep, formdata: Annotated[CreateConvo, Form()]):
    if isinstance(user, RedirectResponse):
        return user
    create_u_convos(id=user.id, doc_id=formdata.id, session=session)
    return Response(content="", status_code=status.HTTP_201_CREATED)


@app.get("/patient/conversation/entries")
def get_convo_entries(user: PatientDep, session: SessionDep, docId: Annotated[str, Query()]):
    if isinstance(user, RedirectResponse):
        return user
    entries = get_conversation_entries(id=user.id, docId=docId, session=session)
    return {"entries": entries}

@app.get("/doctor/conversation/entries")
def get_doc_convo_entries(user: DoctorDep, session: SessionDep, patId: Annotated[str, Query()]):
    if isinstance(user, RedirectResponse):
        return user
    entries = get_doc_conversation_entries(id=user.id, patId=patId, session=session)
    return {"entries": entries}

@app.websocket("/ws")
async def websoc_endp(websocket: WebSocket, session: SessionDep):
    doc = websocket.cookies.get("docid")
    pat = websocket.cookies.get("userid")
    if doc is None and pat is None:
        logger.error(f"Connection failed: doc={doc}, patient={pat}")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthenticated")
    is_doc = doc is not None
    id: str
    if is_doc and doc is not None:
        id = doc
    elif pat is not None:
        # doing the check just to avoid annoying typechecker haha
        id = pat
    await ws_connection_manager.connect(websocket, id=id,is_doc=is_doc)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                m = WebsocketRelayMessage.model_validate_json(data,strict=True)
                d_id = id if is_doc else m.recvid
                p_id = id if not is_doc else m.recvid
                logger.info(f"is_doc={is_doc}")
                c = session.exec(select(Conversation).where(Conversation.doctor_id == d_id,Conversation.patient_id == p_id)).one()
                convEntr = ConversationEntries(from_doctor=is_doc, message=m.msg, conversation_id=c.id)
                session.add(convEntr)
                session.commit()
                session.refresh(convEntr)
                logger.info(f"Conversation entry saved: {convEntr}")
                await ws_connection_manager.relay_message(m.msg, senderid=id, recvid=m.recvid)
            except ValidationError:
                logger.warn(f"Invalid data: {data}")
                await websocket.send_text("invalid data")
    except WebSocketDisconnect:
        await ws_connection_manager.disconnect(id)


    
