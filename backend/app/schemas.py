import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain import Status


class ComplaintIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=10, max_length=2000)
    location: str = Field(min_length=3, max_length=200)
    reporter_contact: str | None = Field(default=None, max_length=200)

    @field_validator("reporter_contact")
    @classmethod
    def _blank_contact_is_none(cls, v: str | None) -> str | None:
        return v or None


class StatusIn(BaseModel):
    status: Status


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str
    location: str
    reporter_contact: str | None
    category: str
    priority: str
    status: str
    ai_summary: str | None
    triaged_by: str
    triage_latency_ms: int | None
    created_at: datetime
    updated_at: datetime


class ComplaintPage(BaseModel):
    items: list[ComplaintOut]
    total: int
    page: int
    page_size: int


class StatsOut(BaseModel):
    total: int
    by_category: dict[str, int]
    by_priority: dict[str, int]
