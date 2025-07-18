from typing import Self
from pydantic import BaseModel, model_validator
from datetime import datetime

class ConvEntry(BaseModel):
    id: int
    time: datetime
    from_doctor: bool
    message: str
    conversation_id: str

class CreateConvo(BaseModel):
    id: str

class Conversation(BaseModel):
    name: str
    id: str


class PatientRegisterFormdata(BaseModel):
    name: str
    email: str
    mdp: str
    cmdp: str

    @model_validator(mode="after")
    def check_passwords_match(self) -> Self:
        assert self.mdp == self.cmdp, "Passwords do not match"
        return self


class PatientM(BaseModel):
    id: str
    name: str
    email: str


class DoctorM(PatientM):
    qualifications: list[str]


class PatientLoginFormData(BaseModel):
    email: str
    mdp: str


class DoctorLoginFormData(PatientLoginFormData):
    pass


class DoctorRegisterModel(PatientRegisterFormdata):
    qualifications: list[str]


class WebsocketRelayMessage(BaseModel):
    msg: str
    recvid: str
