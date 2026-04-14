# Generated from openapi.yaml - DO NOT EDIT MANUALLY
# Run: ./apps/api-lab/openapi/generate.sh python

import uuid
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ReservationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RETURNED = "RETURNED"
    OVERDUE = "OVERDUE"


class Book(BaseModel):
    id: uuid.UUID
    isbn: str
    title: str
    author: str
    genre: str
    published_year: int
    total_copies: int
    available_copies: int
    version: int = 1
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BookCreate(BaseModel):
    isbn: str = Field(pattern=r"^\d{10}(\d{3})?$")
    title: str = Field(min_length=1, max_length=500)
    author: str = Field(min_length=1, max_length=500)
    genre: str = Field(min_length=1, max_length=100)
    published_year: int = Field(ge=1000, le=2027)
    total_copies: int = Field(ge=1)


class BookUpdate(BaseModel):
    isbn: str | None = Field(default=None, pattern=r"^\d{10}(\d{3})?$")
    title: str | None = Field(default=None, min_length=1, max_length=500)
    author: str | None = Field(default=None, min_length=1, max_length=500)
    genre: str | None = Field(default=None, min_length=1, max_length=100)
    published_year: int | None = Field(default=None, ge=1000, le=2027)
    total_copies: int | None = Field(default=None, ge=1)


class Reservation(BaseModel):
    id: uuid.UUID
    book_id: uuid.UUID
    user_id: uuid.UUID
    reserved_at: datetime
    due_date: datetime
    returned_at: datetime | None = None
    status: ReservationStatus

    model_config = {"from_attributes": True}


class ReservationCreate(BaseModel):
    book_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)


class ReservationUpdate(BaseModel):
    status: ReservationStatus


class PaginatedBooks(BaseModel):
    items: list[Book]
    continuation_token: str | None = None
    has_more: bool


class PaginatedReservations(BaseModel):
    items: list[Reservation]
    continuation_token: str | None = None
    has_more: bool


class ListBooksQuery(BaseModel):
    available_only: bool = False
    genre: str | None = Field(default=None, max_length=100)
    author: str | None = Field(default=None, max_length=500)
    search: str | None = Field(default=None, max_length=500)
    limit: int = Field(default=20, ge=1, le=100)
    continuation_token: str | None = None
    sort_by: Literal["title", "author", "published_year", "created_at"] = "created_at"
    sort_order: Literal["asc", "desc"] = "asc"


class ListReservationsQuery(BaseModel):
    user_id: uuid.UUID | None = None
    status: str | None = None
    book_id: uuid.UUID | None = None
    limit: int = Field(default=20, ge=1, le=100)
    continuation_token: str | None = None
    sort_by: Literal["reserved_at", "due_date", "status"] = "reserved_at"
    sort_order: Literal["asc", "desc"] = "desc"


class ErrorResponse(BaseModel):
    detail: str
    status_code: int
    request_id: str | None = None


class HealthResponse(BaseModel):
    status: str


class InfoResponse(BaseModel):
    hostname: str
    app_version: str
    environment: str
    app: str | None = None
    component: str | None = None
    node: str | None = None
    pod_ip: str | None = None
    log_level: str | None = None
    git_tag: str | None = None
    git_commit: str | None = None
