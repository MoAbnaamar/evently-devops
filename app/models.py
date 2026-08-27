from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class FormCreate(BaseModel):
    """What a client sends to create a form."""

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)


class Form(FormCreate):
    """What the API returns: the submitted fields plus server-assigned ones."""

    id: UUID
    created_at: datetime


class SubmissionCreate(BaseModel):
    """A submission is an arbitrary key/value payload.

    The form does not declare its fields yet, so nothing is validated against
    a schema here. See the next steps section of the README.
    """

    data: dict[str, Any]


class Submission(BaseModel):
    id: UUID
    form_id: UUID
    data: dict[str, Any]
    submitted_at: datetime


class Health(BaseModel):
    status: str
    version: str
    environment: str