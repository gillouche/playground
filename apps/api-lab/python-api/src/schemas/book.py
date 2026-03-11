# DEPRECATED: Use generated.models instead. This file kept for backward compatibility.

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class BookBase(BaseModel):
    isbn: str = Field(..., max_length=13)
    title: str
    author: str
    genre: str = Field(..., max_length=100)
    published_year: int
    total_copies: int = Field(..., ge=0)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    isbn: str | None = Field(None, max_length=13)
    title: str | None = None
    author: str | None = None
    genre: str | None = Field(None, max_length=100)
    published_year: int | None = None
    total_copies: int | None = Field(None, ge=0)


class BookResponse(BookBase):
    id: uuid.UUID
    available_copies: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReservationCreate(BaseModel):
    user_id: str
    book_ids: list[uuid.UUID]


class ReservationResponse(BaseModel):
    id: uuid.UUID
    book_id: uuid.UUID
    user_id: str
    reserved_at: datetime
    due_date: datetime
    returned_at: datetime | None = None
    status: str

    model_config = {"from_attributes": True}


class InventoryResponse(BaseModel):
    items: list[BookResponse]


class ErrorResponse(BaseModel):
    detail: str
    status_code: int


class HealthResponse(BaseModel):
    status: str


class InfoResponse(BaseModel):
    hostname: str | None = None
    app_version: str | None = None
    environment: str | None = None
    app: str | None = None
    component: str | None = None
    node: str | None = None
    pod_ip: str | None = None
    log_level: str | None = None
    git_tag: str | None = None
    git_commit: str | None = None
