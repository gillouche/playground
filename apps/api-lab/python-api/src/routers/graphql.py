import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import strawberry
from schemas.book import BookCreate, BookUpdate, ReservationCreate
from services.book_service import BookService
from strawberry.fastapi import GraphQLRouter

# These will be set during app startup
_book_service: BookService | None = None


def set_book_service(service: BookService):
    global _book_service  # noqa: PLW0603
    _book_service = service


def _get_service() -> BookService:
    assert _book_service is not None, "BookService not initialized"
    return _book_service


@strawberry.type
@dataclass
class BookType:
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


@strawberry.type
@dataclass
class ReservationType:
    id: uuid.UUID
    book_id: uuid.UUID
    user_id: str
    reserved_at: datetime
    due_date: datetime
    returned_at: datetime | None
    status: str


@strawberry.type
@dataclass
class InventoryType:
    items: list[BookType]


def _to_book_type(book: Any) -> BookType:
    return BookType(
        id=book.id,
        isbn=book.isbn,
        title=book.title,
        author=book.author,
        genre=book.genre,
        published_year=book.published_year,
        total_copies=book.total_copies,
        available_copies=book.available_copies,
        created_at=book.created_at,
        updated_at=book.updated_at,
    )


def _to_reservation_type(reservation: Any) -> ReservationType:
    return ReservationType(
        id=reservation.id,
        book_id=reservation.book_id,
        user_id=reservation.user_id,
        reserved_at=reservation.reserved_at,
        due_date=reservation.due_date,
        returned_at=reservation.returned_at,
        status=reservation.status,
    )


@strawberry.type
class Query:
    @strawberry.field
    async def books(
        self,
        available_only: bool = False,
        genre: str | None = None,
        author: str | None = None,
        search: str | None = None,
    ) -> list[BookType]:
        service = _get_service()
        results = await service.list_books(
            available_only=available_only, genre=genre, author=author, search=search
        )
        return [_to_book_type(b) for b in results]

    @strawberry.field
    async def book(self, book_id: uuid.UUID) -> BookType | None:
        service = _get_service()
        result = await service.get_book(book_id)
        return _to_book_type(result) if result else None

    @strawberry.field
    async def inventory(self) -> list[BookType]:
        service = _get_service()
        results = await service.get_inventory()
        return [_to_book_type(b) for b in results]

    @strawberry.field
    async def reservations(
        self,
        user_id: str | None = None,
        status: str | None = None,
        book_id: uuid.UUID | None = None,
    ) -> list[ReservationType]:
        service = _get_service()
        results = await service.list_reservations(user_id=user_id, status=status, book_id=book_id)
        return [_to_reservation_type(r) for r in results]

    @strawberry.field
    async def reservation(self, reservation_id: uuid.UUID) -> ReservationType | None:
        service = _get_service()
        result = await service.get_reservation(reservation_id)
        return _to_reservation_type(result) if result else None


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_book(  # noqa: PLR0913
        self,
        isbn: str,
        title: str,
        author: str,
        genre: str,
        published_year: int,
        total_copies: int,
    ) -> BookType:
        service = _get_service()
        data = BookCreate(
            isbn=isbn,
            title=title,
            author=author,
            genre=genre,
            published_year=published_year,
            total_copies=total_copies,
        )
        result = await service.create_book(data)
        return _to_book_type(result)

    @strawberry.mutation
    async def update_book(  # noqa: PLR0913
        self,
        book_id: uuid.UUID,
        isbn: str | None = None,
        title: str | None = None,
        author: str | None = None,
        genre: str | None = None,
        published_year: int | None = None,
        total_copies: int | None = None,
    ) -> BookType | None:
        service = _get_service()
        data = BookUpdate(
            isbn=isbn,
            title=title,
            author=author,
            genre=genre,
            published_year=published_year,
            total_copies=total_copies,
        )
        result = await service.update_book(book_id, data)
        return _to_book_type(result) if result else None

    @strawberry.mutation
    async def delete_book(self, book_id: uuid.UUID) -> bool:
        service = _get_service()
        result: bool = await service.delete_book(book_id)
        return result

    @strawberry.mutation
    async def reserve_books(self, user_id: str, book_ids: list[uuid.UUID]) -> list[ReservationType]:
        service = _get_service()
        data = ReservationCreate(user_id=user_id, book_ids=book_ids)
        results = await service.reserve_books(data)
        return [_to_reservation_type(r) for r in results]

    @strawberry.mutation
    async def return_reservation(self, reservation_id: uuid.UUID) -> ReservationType | None:
        service = _get_service()
        result = await service.return_reservation(reservation_id)
        return _to_reservation_type(result) if result else None


schema = strawberry.Schema(query=Query, mutation=Mutation)


def create_graphql_router(graphiql: bool = True) -> GraphQLRouter:
    return GraphQLRouter(schema, path="/graphql", graphql_ide="graphiql" if graphiql else None)
