from dataclasses import dataclass
import logging
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select
from iot_proj.form_models import ConvEntry, Conversation, PatientLoginFormData, PatientM, PatientRegisterFormdata
from iot_proj.models import ConversationEntries, Patient, Conversation as ConvoT
from passlib.hash import pbkdf2_sha256


log = logging.getLogger(__name__)
@dataclass
class Error:
    error: str

def hash_pwd(pwd: str) -> str:
    return pbkdf2_sha256.hash(pwd)

def pwdmatch(pwd: str, hash: str) -> bool:
    return pbkdf2_sha256.verify(pwd, hash)

def create_patient(formdata: PatientRegisterFormdata, session: Session) -> Patient | Error:
    hash = hash_pwd(formdata.mdp)
    patient = Patient(name = formdata.name, email = formdata.email, password=hash)
    try:
        session.add(patient)
        session.commit()
        session.refresh(patient)
    except SQLAlchemyError as e:
        log.error(f"Failed to insert user: Cause: {e}")
        return Error(f"Error adding user, {e._message}")
    return patient


def get_user(formdata: PatientLoginFormData, session: Session) -> PatientM | Error:
    try:
        res = session.exec(select(Patient).where(Patient.email == formdata.email)).one_or_none()
        if res is None:
            return Error("No entry found")
        pwd_match = pwdmatch(formdata.mdp, res.password)
        if not pwd_match:
            return Error("Wrong credentials")
        return PatientM(name=res.name, email=res.email, id=res.id)
    except SQLAlchemyError as e:
        log.error(e)
        return Error(f"Error adding user, {e._message}")
    

def get_user_convos(id: str, session: Session) -> list[Conversation | None] | Error:
    try:
        res = session.exec(select(ConvoT).where(ConvoT.patient_id == id)).all()
        convos = list(map(map_u_convo, res))
        return convos
    except SQLAlchemyError as e:
        log.error(f"Failed to get user: Cause: {e}")
        return Error(f"Error getting user, {e._message}")

def get_conversation_entries(id: str, docId: str, session: Session) -> list[ConvEntry | None]:
        res = session.exec(select(ConvoT).where(ConvoT.patient_id == id, ConvoT.doctor_id == docId)).one()
        conversations = res.conversations
        return list(map(conv_to_ConvEnt, conversations))


def conv_to_ConvEnt(conv: ConversationEntries) -> ConvEntry | None:
    if conv.id is not None:
        return ConvEntry(id=conv.id, from_doctor=conv.from_doctor, time=conv.time, message=conv.message, conversation_id=conv.conversation_id)
    return None
    
    

def create_u_convos(id: str, doc_id: str, session: Session):
    try:
        c = ConvoT(doctor_id=doc_id, patient_id=id)
        session.add(c)
        session.commit()
    except SQLAlchemyError as e:
        log.error(e)
        pass


def map_u_convo(conv: ConvoT) -> Conversation | None:
    if conv.doctor is None:
        return None
    return Conversation(name=conv.doctor.name, id=conv.doctor_id)
