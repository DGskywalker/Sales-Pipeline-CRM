from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import STAGES

EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class ContactIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: str = Field(..., pattern=EMAIL_RE, max_length=255)
    company: Optional[str] = Field(None, max_length=160)
    phone: Optional[str] = Field(None, max_length=40)
    source: Optional[str] = Field(None, max_length=60)

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.strip().lower()


class ContactUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    company: Optional[str] = Field(None, max_length=160)
    phone: Optional[str] = Field(None, max_length=40)
    source: Optional[str] = Field(None, max_length=60)


class ContactOut(ContactIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class DealIn(BaseModel):
    contact_id: int
    title: str = Field(..., min_length=1, max_length=160)
    value: float = Field(0, ge=0)
    stage: str = "Lead"
    owner: Optional[str] = Field(None, max_length=80)

    @field_validator("stage")
    @classmethod
    def valid_stage(cls, v: str) -> str:
        if v not in STAGES:
            raise ValueError(f"stage must be one of {STAGES}")
        return v


class DealUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=160)
    value: Optional[float] = Field(None, ge=0)
    stage: Optional[str] = None
    owner: Optional[str] = Field(None, max_length=80)

    @field_validator("stage")
    @classmethod
    def valid_stage(cls, v):
        if v is not None and v not in STAGES:
            raise ValueError(f"stage must be one of {STAGES}")
        return v


class DealOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    contact_id: int
    title: str
    value: float
    stage: str
    owner: Optional[str]
    contact_name: Optional[str] = None
    company: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ActivityIn(BaseModel):
    type: str = Field("note", pattern="^(note|call|email|meeting)$")
    note: str = Field("", max_length=2000)


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    deal_id: int
    type: str
    note: str
    created_at: datetime


class FeedItem(ActivityOut):
    deal_title: str
    company: Optional[str]


class OwnerStats(BaseModel):
    owner: str
    open_deals: int
    open_value: float
    won_deals: int
    won_value: float
    win_rate: Optional[float]
