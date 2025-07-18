import uuid
from typing import Annotated

from fastapi import Cookie, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from iot_proj.doctor_services import str_to_qualifications
from iot_proj.form_models import DoctorM, PatientM
from iot_proj.models import Doctor, Patient, SessionDep


def get_patient(request: Request, session: SessionDep,  userid: Annotated[str | None, Cookie()] = None) -> PatientM | RedirectResponse:
    if userid is None:
        return RedirectResponse(request.url_for("patient_login"))
    try:
        uuid.UUID(userid, version=4)
    except ValueError:
        return RedirectResponse(request.url_for("patient_login"))
    try:
        patient = session.exec(select(Patient).where(Patient.id == userid)).one_or_none()
        if patient is None:
            return RedirectResponse(request.url_for("patient_login"))
        return PatientM(name=patient.name, email=patient.email, id=patient.id)
    except SQLAlchemyError as e:
        from iot_proj import logger as log
        log.error(f"Couldn't fetch user: {e}")
        return RedirectResponse(request.url_for("patient_login"))



def get_doctor(request: Request, session: SessionDep,  docid: Annotated[str | None, Cookie()] = None) -> DoctorM | RedirectResponse:
    if docid is None:
        return RedirectResponse(request.url_for("doctor_login"))
    try:
        uuid.UUID(docid, version=4)
    except ValueError:
        return RedirectResponse(request.url_for("doctor_login"))
    try:
        doctor = session.exec(select(Doctor).where(Doctor.id == docid)).one_or_none()
        if doctor is None:
            return RedirectResponse(request.url_for("doctor_login"))
        return DoctorM(name=doctor.name, email=doctor.email, id=doctor.id, qualifications=str_to_qualifications(doctor.qualifications))
    except SQLAlchemyError as e:
        from iot_proj import logger as log
        log.error(f"Couldn't fetch user: {e}")
        return RedirectResponse(request.url_for("doctor_login"))
