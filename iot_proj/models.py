import uuid
from typing import Annotated, Optional

from fastapi import Depends
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine
from datetime import datetime


def create_uuid() -> str:
    return f"{uuid.uuid4()}"

class Patient(SQLModel, table=True):
    id: str = Field(default_factory=create_uuid, primary_key=True)
    email: str = Field(index=True, unique=True)
    password: str
    name: str
    conversations: list["Conversation"] = Relationship(back_populates="patient")

class Doctor(SQLModel, table=True):
    id: str = Field(default_factory=create_uuid, primary_key=True)
    email: str = Field(index=True, unique=True)
    password: str
    name: str
    qualifications: str
    conversations: list["Conversation"] = Relationship(back_populates="doctor")

class Conversation(SQLModel, table=True):
    id: str = Field(default_factory=create_uuid, primary_key=True)
    doctor_id: str = Field(foreign_key="doctor.id", primary_key=True)
    patient_id: str = Field(foreign_key="patient.id", primary_key=True)
    doctor: Optional[Doctor] = Relationship(back_populates="conversations")
    patient: Optional[Patient] = Relationship(back_populates="conversations")
    conversations: list["ConversationEntries"] = Relationship(back_populates="conversation")

class ConversationEntries(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    time: datetime = Field(default_factory=datetime.now)
    from_doctor: bool
    message: str
    conversation_id: str = Field(foreign_key="conversation.id")
    conversation: Conversation = Relationship(back_populates="conversations")

db_file = "db.sqlite3"
db_url = f"sqlite:///{db_file}"

connect_args = {"check_same_thread": False}
engine = create_engine(db_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
