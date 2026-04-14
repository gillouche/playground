import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import strawberry
from client import LibraryClient, ListBooksParams, ListReservationsParams
from graphql import GraphQLError, GraphQLList, GraphQLNonNull, GraphQLSchema
from graphql.language import FieldNode, FragmentSpreadNode, InlineFragmentNode, SelectionSetNode
from graphql.validation import ValidationContext, ValidationRule
from strawberry.extensions import AddValidationRules, DisableIntrospection, QueryDepthLimiter
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info
from tracing_extension import OpenTelemetryExtension

_client: LibraryClient | None = None


def set_client(client: LibraryClient):
    global _client  # noqa: PLW0603
    _client = client


def _get_client() -> LibraryClient:
    assert _client is not None, "LibraryClient not initialized"
    return _client


def _get_auth_headers(info: Info) -> dict[str, str] | None:
    request = info.context.get("request")
    if not request:
        return None
    auth = request.headers.get("authorization")
    if not auth:
        return None
    return {"authorization": auth}


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
        info: Info,
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
        headers = _get_auth_headers(info)
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
        result = await client.list_books(params, headers=headers)
        return PaginatedBooksType(
            items=[_to_book_type(b) for b in result["items"]],
            continuation_token=result.get("continuation_token"),
            has_more=result.get("has_more", False),
        )

    @strawberry.field
    async def book(self, info: Info, book_id: uuid.UUID) -> BookType | None:
        client = _get_client()
        headers = _get_auth_headers(info)
        result = await client.get_book(book_id, headers=headers)
        return _to_book_type(result) if result else None

    @strawberry.field
    async def reservations(  # noqa: PLR0913
        self,
        info: Info,
        user_id: uuid.UUID | None = None,
        status: str | None = None,
        book_id: uuid.UUID | None = None,
        limit: int | None = None,
        continuation_token: str | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> PaginatedReservationsType:
        client = _get_client()
        headers = _get_auth_headers(info)
        params = ListReservationsParams(
            user_id=str(user_id) if user_id else None,
            status=status,
            book_id=str(book_id) if book_id else None,
            limit=limit,
            continuation_token=continuation_token,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        result = await client.list_reservations(params, headers=headers)
        return PaginatedReservationsType(
            items=[_to_reservation_type(r) for r in result["items"]],
            continuation_token=result.get("continuation_token"),
            has_more=result.get("has_more", False),
        )

    @strawberry.field
    async def reservation(self, info: Info, reservation_id: uuid.UUID) -> ReservationType | None:
        client = _get_client()
        headers = _get_auth_headers(info)
        result = await client.get_reservation(reservation_id, headers=headers)
        return _to_reservation_type(result) if result else None


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_book(  # noqa: PLR0913
        self,
        info: Info,
        isbn: str,
        title: str,
        author: str,
        genre: str,
        published_year: int,
        total_copies: int,
    ) -> BookType:
        client = _get_client()
        headers = _get_auth_headers(info)
        result = await client.create_book(
            {
                "isbn": isbn,
                "title": title,
                "author": author,
                "genre": genre,
                "published_year": published_year,
                "total_copies": total_copies,
            },
            headers=headers,
        )
        return _to_book_type(result)

    @strawberry.mutation
    async def update_book(  # noqa: PLR0913
        self,
        info: Info,
        book_id: uuid.UUID,
        isbn: str | None = None,
        title: str | None = None,
        author: str | None = None,
        genre: str | None = None,
        published_year: int | None = None,
        total_copies: int | None = None,
    ) -> BookType | None:
        client = _get_client()
        headers = _get_auth_headers(info)
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
        result = await client.update_book(book_id, data, headers=headers)
        return _to_book_type(result) if result else None

    @strawberry.mutation
    async def delete_book(self, info: Info, book_id: uuid.UUID) -> bool:
        client = _get_client()
        headers = _get_auth_headers(info)
        return bool(await client.delete_book(book_id, headers=headers))

    @strawberry.mutation
    async def reserve_books(
        self, info: Info, user_id: uuid.UUID, book_ids: list[uuid.UUID]
    ) -> list[ReservationType]:
        client = _get_client()
        headers = _get_auth_headers(info)
        results = await client.reserve_books(
            str(user_id), [str(bid) for bid in book_ids], headers=headers
        )
        return [_to_reservation_type(r) for r in results]

    @strawberry.mutation
    async def update_reservation(
        self, info: Info, reservation_id: uuid.UUID, status: str
    ) -> ReservationType | None:
        client = _get_client()
        headers = _get_auth_headers(info)
        result = await client.update_reservation(reservation_id, status=status, headers=headers)
        return _to_reservation_type(result) if result else None


_MAX_QUERY_DEPTH = 10
_MAX_QUERY_COMPLEXITY = 1000
_LIST_FIELD_COST = 10
_DEFAULT_FIELD_COST = 1


def _is_list_type(graphql_type: Any) -> bool:
    if isinstance(graphql_type, GraphQLNonNull):
        return _is_list_type(graphql_type.of_type)
    return isinstance(graphql_type, GraphQLList)


def _compute_complexity(
    selection_set: SelectionSetNode,
    parent_type: Any,
    schema: GraphQLSchema,
    fragments: dict,
) -> int:
    total = 0
    for selection in selection_set.selections:
        if isinstance(selection, FieldNode):
            field_name = selection.name.value
            if field_name.startswith("__"):
                continue
            field_def = None
            if hasattr(parent_type, "fields"):
                field_def = parent_type.fields.get(field_name)
            cost = (
                _LIST_FIELD_COST
                if (field_def and _is_list_type(field_def.type))
                else _DEFAULT_FIELD_COST
            )
            total += cost
            if selection.selection_set and field_def:
                field_type = field_def.type
                while isinstance(field_type, GraphQLNonNull | GraphQLList):
                    field_type = field_type.of_type
                total += _compute_complexity(selection.selection_set, field_type, schema, fragments)
        elif isinstance(selection, InlineFragmentNode) and selection.selection_set:
            type_name = selection.type_condition.name.value if selection.type_condition else None
            inline_type = schema.type_map.get(type_name) if type_name else parent_type
            total += _compute_complexity(
                selection.selection_set, inline_type or parent_type, schema, fragments
            )
        elif isinstance(selection, FragmentSpreadNode):
            fragment = fragments.get(selection.name.value)
            if fragment and fragment.selection_set:
                type_name = fragment.type_condition.name.value if fragment.type_condition else None
                frag_type = schema.type_map.get(type_name) if type_name else parent_type
                total += _compute_complexity(
                    fragment.selection_set, frag_type or parent_type, schema, fragments
                )
    return total


def _create_complexity_validator(max_complexity: int) -> type[ValidationRule]:
    class ComplexityValidator(ValidationRule):
        def __init__(self, validation_context: ValidationContext) -> None:
            super().__init__(validation_context)
            schema = validation_context.schema
            document = validation_context.document
            fragments = {
                defn.name.value: defn
                for defn in document.definitions
                if hasattr(defn, "type_condition")
            }
            for defn in document.definitions:
                if not hasattr(defn, "operation"):
                    continue
                operation = (
                    defn.operation.value
                    if hasattr(defn.operation, "value")
                    else str(defn.operation)
                )
                if operation == "mutation":
                    root_type = schema.mutation_type
                elif operation == "subscription":
                    root_type = schema.subscription_type
                else:
                    root_type = schema.query_type
                if root_type is None or not defn.selection_set:
                    continue
                complexity = _compute_complexity(defn.selection_set, root_type, schema, fragments)
                if complexity > max_complexity:
                    self.report_error(
                        GraphQLError(
                            f"Query complexity {complexity} exceeds maximum allowed complexity of {max_complexity}"
                        )
                    )

    return ComplexityValidator


def _build_extensions() -> list:
    extensions: list = [
        OpenTelemetryExtension,
        QueryDepthLimiter(max_depth=_MAX_QUERY_DEPTH),
        AddValidationRules([_create_complexity_validator(_MAX_QUERY_COMPLEXITY)]),
    ]
    env = os.environ.get("ENVIRONMENT", "dev")
    if env == "prod":
        extensions.append(DisableIntrospection())
    return extensions


graphql_schema = strawberry.Schema(query=Query, mutation=Mutation, extensions=_build_extensions())


def create_graphql_router(graphiql: bool = True) -> GraphQLRouter:
    return GraphQLRouter(
        graphql_schema, path="/graphql", graphql_ide="graphiql" if graphiql else None
    )
