import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import strawberry
from client import LibraryClient, ListBooksParams, ListReservationsParams
from strawberry.fastapi import GraphQLRouter
from tracing_extension import OpenTelemetryExtension

_client: LibraryClient | None = None


def set_client(client: LibraryClient):
    global _client  # noqa: PLW0603
    _client = client


def _get_client() -> LibraryClient:
    assert _client is not None, "LibraryClient not initialized"
    return _client


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
    user_id: uuid.UUID
    reserved_at: datetime
    due_date: datetime
    returned_at: datetime | None
    status: str


@strawberry.type
@dataclass
class PaginatedBooksType:
    items: list[BookType]
    continuation_token: str | None
    has_more: bool


@strawberry.type
@dataclass
class PaginatedReservationsType:
    items: list[ReservationType]
    continuation_token: str | None
    has_more: bool


def _to_book_type(data: dict[str, Any]) -> BookType:
    return BookType(
        id=uuid.UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
        isbn=data["isbn"],
        title=data["title"],
        author=data["author"],
        genre=data["genre"],
        published_year=data["published_year"],
        total_copies=data["total_copies"],
        available_copies=data["available_copies"],
        created_at=datetime.fromisoformat(data["created_at"])
        if isinstance(data["created_at"], str)
        else data["created_at"],
        updated_at=datetime.fromisoformat(data["updated_at"])
        if isinstance(data["updated_at"], str)
        else data["updated_at"],
    )


def _to_reservation_type(data: dict[str, Any]) -> ReservationType:
    return ReservationType(
        id=uuid.UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
        book_id=uuid.UUID(data["book_id"]) if isinstance(data["book_id"], str) else data["book_id"],
        user_id=uuid.UUID(data["user_id"]) if isinstance(data["user_id"], str) else data["user_id"],
        reserved_at=datetime.fromisoformat(data["reserved_at"])
        if isinstance(data["reserved_at"], str)
        else data["reserved_at"],
        due_date=datetime.fromisoformat(data["due_date"])
        if isinstance(data["due_date"], str)
        else data["due_date"],
        returned_at=datetime.fromisoformat(data["returned_at"])
        if isinstance(data["returned_at"], str) and data["returned_at"]
        else data.get("returned_at"),
        status=data["status"],
    )


@strawberry.type
class Query:
    @strawberry.field
    async def books(  # noqa: PLR0913
        self,
        available_only: bool = False,
        genre: str | None = None,
        author: str | None = None,
        search: str | None = None,
        limit: int | None = None,
        continuation_token: str | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> PaginatedBooksType:
        client = _get_client()
        params = ListBooksParams(
            available_only=available_only,
            genre=genre,
            author=author,
            search=search,
            limit=limit,
            continuation_token=continuation_token,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        result = await client.list_books(params)
        return PaginatedBooksType(
            items=[_to_book_type(b) for b in result["items"]],
            continuation_token=result.get("continuation_token"),
            has_more=result.get("has_more", False),
        )

    @strawberry.field
    async def book(self, book_id: uuid.UUID) -> BookType | None:
        client = _get_client()
        result = await client.get_book(book_id)
        return _to_book_type(result) if result else None

    @strawberry.field
    async def reservations(  # noqa: PLR0913
        self,
        user_id: uuid.UUID | None = None,
        status: str | None = None,
        book_id: uuid.UUID | None = None,
        limit: int | None = None,
        continuation_token: str | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> PaginatedReservationsType:
        client = _get_client()
        params = ListReservationsParams(
            user_id=str(user_id) if user_id else None,
            status=status,
            book_id=str(book_id) if book_id else None,
            limit=limit,
            continuation_token=continuation_token,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        result = await client.list_reservations(params)
        return PaginatedReservationsType(
            items=[_to_reservation_type(r) for r in result["items"]],
            continuation_token=result.get("continuation_token"),
            has_more=result.get("has_more", False),
        )

    @strawberry.field
    async def reservation(self, reservation_id: uuid.UUID) -> ReservationType | None:
        client = _get_client()
        result = await client.get_reservation(reservation_id)
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
        client = _get_client()
        result = await client.create_book(
            {
                "isbn": isbn,
                "title": title,
                "author": author,
                "genre": genre,
                "published_year": published_year,
                "total_copies": total_copies,
            }
        )
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
        client = _get_client()
        data: dict[str, Any] = {}
        if isbn is not None:
            data["isbn"] = isbn
        if title is not None:
            data["title"] = title
        if author is not None:
            data["author"] = author
        if genre is not None:
            data["genre"] = genre
        if published_year is not None:
            data["published_year"] = published_year
        if total_copies is not None:
            data["total_copies"] = total_copies
        result = await client.update_book(book_id, data)
        return _to_book_type(result) if result else None

    @strawberry.mutation
    async def delete_book(self, book_id: uuid.UUID) -> bool:
        client = _get_client()
        return bool(await client.delete_book(book_id))

    @strawberry.mutation
    async def reserve_books(
        self, user_id: uuid.UUID, book_ids: list[uuid.UUID]
    ) -> list[ReservationType]:
        client = _get_client()
        results = await client.reserve_books(str(user_id), [str(bid) for bid in book_ids])
        return [_to_reservation_type(r) for r in results]

    @strawberry.mutation
    async def update_reservation(
        self, reservation_id: uuid.UUID, status: str
    ) -> ReservationType | None:
        client = _get_client()
        result = await client.update_reservation(reservation_id, status=status)
        return _to_reservation_type(result) if result else None


graphql_schema = strawberry.Schema(
    query=Query, mutation=Mutation, extensions=[OpenTelemetryExtension]
)


def create_graphql_router(graphiql: bool = True) -> GraphQLRouter:
    return GraphQLRouter(
        graphql_schema, path="/graphql", graphql_ide="graphiql" if graphiql else None
    )
