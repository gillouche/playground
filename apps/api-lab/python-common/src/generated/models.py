# Generated from openapi.yaml - DO NOT EDIT MANUALLY
# Run: ./apps/api-lab/openapi/generate.sh python

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


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
    isbn: str
    title: str
    author: str
    genre: str
    published_year: int
    total_copies: int


class BookUpdate(BaseModel):
    isbn: str | None = None
    title: str | None = None
    author: str | None = None
    genre: str | None = None
    published_year: int | None = None
    total_copies: int | None = None


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
    user_id: uuid.UUID
    book_ids: list[uuid.UUID]


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
    genre: str | None = None
    author: str | None = None
    search: str | None = None
    limit: int = 20
    continuation_token: str | None = None
    sort_by: str = "created_at"
    sort_order: str = "asc"


class ListReservationsQuery(BaseModel):
    user_id: uuid.UUID | None = None
    status: str | None = None
    book_id: uuid.UUID | None = None
    limit: int = 20
    continuation_token: str | None = None
    sort_by: str = "reserved_at"
    sort_order: str = "desc"


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
