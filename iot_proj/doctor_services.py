import logging
from functools import reduce

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from iot_proj.form_models import DoctorLoginFormData, DoctorM, DoctorRegisterModel, Conversation, ConvEntry
from iot_proj.models import Doctor, Conversation as ConvoT
from iot_proj.user_services import Error, conv_to_ConvEnt, hash_pwd, pwdmatch

log = logging.getLogger(__name__)
def __qualifications_to_str(qualis: list[str]) -> str:
    return reduce(lambda a,b: a + "," + b, qualis, "")

def str_to_qualifications(qualis: str) -> list[str]:
    q = qualis.split(',')
    q = filter(lambda a: len(a.strip()) != 0, q)
    return list(q)

def create_doctor(formdata: DoctorRegisterModel, session: Session) -> Doctor | Error:
    hash = hash_pwd(formdata.mdp)
    doctor = Doctor(name=formdata.name, email=formdata.email, password=hash, qualifications=__qualifications_to_str(formdata.qualifications))
    try:
        session.add(doctor)
        session.commit()
        session.refresh(doctor)
    except SQLAlchemyError as e:
        log.error(f"Failed to insert user: Cause: {e}")
        return Error(f"Error adding user, {e._message}")
    return doctor

def get_doctor(formdata: DoctorLoginFormData, session: Session):
    try:
        res = session.exec(select(Doctor).where(Doctor.email == formdata.email)).one_or_none()
        if res is None:
            return Error("No entry found")
        pwd_match = pwdmatch(formdata.mdp, res.password)
        if not pwd_match:
            return Error("Wrong credentials")
        return DoctorM(id=res.id, name=res.name, email=res.email, qualifications=str_to_qualifications(res.qualifications))
    except SQLAlchemyError as e:
        log.error(f"Failed to get user: Cause: {e}")
        return Error(f"Error getting user, {e._message}")
        


def get_doctor_by_id(id: str, session: Session) -> DoctorM | Error:
    try:
        res = session.exec(select(Doctor).where(Doctor.id == id)).one_or_none()
        if res is None:
            return Error("No entry found")
        return DoctorM(id=res.id, name=res.name, email=res.email, qualifications=str_to_qualifications(res.qualifications))
    except SQLAlchemyError as e:
        log.error(f"Failed to get user: Cause: {e}")
        return Error(f"Error getting user, {e._message}")


def get_doc_convos(id: str, session: Session) -> list[Conversation | None] | Error:
    try:
        res = session.exec(select(ConvoT).where(ConvoT.doctor_id == id)).all()
        convos = list(map(map_d_convo, res))
        return convos
    except SQLAlchemyError as e:
        log.error(f"Failed to get user: Cause: {e}")
        return Error(f"Error getting user, {e._message}")


def map_d_convo(conv: ConvoT) -> Conversation | None:
    if conv.patient is None:
        return None
    return Conversation(name=conv.patient.name, id=conv.patient_id)



def get_doc_conversation_entries(id: str, patId: str, session: Session) -> list[ConvEntry | None]:
        res = session.exec(select(ConvoT).where(ConvoT.patient_id == patId, ConvoT.doctor_id == id)).one()
        conversations = res.conversations
        log.info(f"Conversation entries count: {len(conversations)}")
        return list(map(conv_to_ConvEnt, conversations))
