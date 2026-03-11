# Generated from openapi.yaml - DO NOT EDIT MANUALLY
# Run: ./apps/api-lab/openapi/generate.sh python

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    import uuid
    from datetime import datetime

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ReservationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RETURNED = "RETURNED"
    OVERDUE = "OVERDUE"


# ---------------------------------------------------------------------------
# Core schemas
# ---------------------------------------------------------------------------


class Book(BaseModel):
    id: uuid.UUID
    isbn: str
    title: str
    author: str
    genre: str
    published_year: int
    total_copies: int
    available_copies: int
    created_at: datetime
    updated_at: datetime


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


class BookResponse(Book):
    model_config = {"from_attributes": True}


class Reservation(BaseModel):
    id: uuid.UUID
    book_id: uuid.UUID
    user_id: str
    reserved_at: datetime
    due_date: datetime
    returned_at: datetime | None = None
    status: ReservationStatus


class ReservationCreate(BaseModel):
    user_id: str
    book_ids: list[uuid.UUID]


class ReservationResponse(Reservation):
    model_config = {"from_attributes": True}


class InventoryResponse(BaseModel):
    items: list[Book]

    model_config = {"from_attributes": True}


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
