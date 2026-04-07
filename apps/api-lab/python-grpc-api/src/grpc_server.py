import logging
import uuid

import grpc
from generated.models import (
    BookCreate,
    BookUpdate,
    ListBooksQuery,
    ListReservationsQuery,
    ReservationCreate,
)
from google.protobuf import timestamp_pb2
from grpc import aio
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from library.v1 import library_pb2, library_pb2_grpc
from observability.tracing import get_tracer
from services.book_service import (
    ActiveReservationsError,
    BookService,
    DuplicateISBNError,
    StaleVersionError,
)

logger = logging.getLogger("api-lab.grpc")

_tracer = get_tracer("api-lab.grpc_server")

_RESERVATION_STATUS_MAP = {
    "ACTIVE": library_pb2.RESERVATION_STATUS_ACTIVE,
    "RETURNED": library_pb2.RESERVATION_STATUS_RETURNED,
    "OVERDUE": library_pb2.RESERVATION_STATUS_OVERDUE,
}

_BOOK_SORT_FIELD_MAP = {
    library_pb2.BOOK_SORT_FIELD_UNSPECIFIED: "created_at",
    library_pb2.BOOK_SORT_FIELD_TITLE: "title",
    library_pb2.BOOK_SORT_FIELD_AUTHOR: "author",
    library_pb2.BOOK_SORT_FIELD_PUBLISHED_YEAR: "published_year",
    library_pb2.BOOK_SORT_FIELD_CREATED_AT: "created_at",
}

_RESERVATION_SORT_FIELD_MAP = {
    library_pb2.RESERVATION_SORT_FIELD_UNSPECIFIED: "reserved_at",
    library_pb2.RESERVATION_SORT_FIELD_RESERVED_AT: "reserved_at",
    library_pb2.RESERVATION_SORT_FIELD_DUE_DATE: "due_date",
    library_pb2.RESERVATION_SORT_FIELD_STATUS: "status",
}

_SORT_ORDER_MAP = {
    library_pb2.SORT_ORDER_UNSPECIFIED: "asc",
    library_pb2.SORT_ORDER_ASC: "asc",
    library_pb2.SORT_ORDER_DESC: "desc",
}

_RESERVATION_STATUS_PROTO_TO_STRING = {
    library_pb2.RESERVATION_STATUS_UNSPECIFIED: None,
    library_pb2.RESERVATION_STATUS_ACTIVE: "ACTIVE",
    library_pb2.RESERVATION_STATUS_RETURNED: "RETURNED",
    library_pb2.RESERVATION_STATUS_OVERDUE: "OVERDUE",
}

_UPDATE_MASK_FIELD_NAMES = {"isbn", "title", "author", "genre", "published_year", "total_copies"}


def _datetime_to_timestamp(dt):
    ts = timestamp_pb2.Timestamp()
    ts.FromDatetime(dt)
    return ts


def _book_to_proto(book) -> library_pb2.Book:
    return library_pb2.Book(
        id=str(book.id),
        isbn=book.isbn,
        title=book.title,
        author=book.author,
        genre=book.genre,
        published_year=book.published_year,
        total_copies=book.total_copies,
        available_copies=book.available_copies,
        version=book.version,
        created_at=_datetime_to_timestamp(book.created_at),
        updated_at=_datetime_to_timestamp(book.updated_at),
    )


def _reservation_to_proto(reservation) -> library_pb2.Reservation:
    status_str = (
        reservation.status if isinstance(reservation.status, str) else reservation.status.value
    )
    proto_status = _RESERVATION_STATUS_MAP.get(
        status_str, library_pb2.RESERVATION_STATUS_UNSPECIFIED
    )

    kwargs = {
        "id": str(reservation.id),
        "book_id": str(reservation.book_id),
        "user_id": str(reservation.user_id),
        "reserved_at": _datetime_to_timestamp(reservation.reserved_at),
        "due_date": _datetime_to_timestamp(reservation.due_date),
        "status": proto_status,
    }
    if reservation.returned_at is not None:
        kwargs["returned_at"] = _datetime_to_timestamp(reservation.returned_at)
    return library_pb2.Reservation(**kwargs)


def _build_update_kwargs(request) -> dict:
    if request.HasField("update_mask") and request.update_mask.paths:
        return {
            path: getattr(request, path)
            for path in request.update_mask.paths
            if path in _UPDATE_MASK_FIELD_NAMES
        }
    kwargs = {}
    for field_name in _UPDATE_MASK_FIELD_NAMES:
        if request.HasField(field_name):
            kwargs[field_name] = getattr(request, field_name)
    return kwargs


class LibraryServiceServicer(library_pb2_grpc.LibraryServiceServicer):
    def __init__(self, book_service: BookService):
        self._service = book_service

    async def ListBooks(self, request, _context):
        with _tracer.start_as_current_span("grpc.ListBooks"):
            query = ListBooksQuery(
                available_only=request.available_only,
                genre=request.genre or None,
                author=request.author or None,
                search=request.search or None,
                limit=request.page_size or 20,
                continuation_token=request.page_token or None,
                sort_by=_BOOK_SORT_FIELD_MAP.get(request.sort_by, "created_at"),
                sort_order=_SORT_ORDER_MAP.get(request.sort_order, "asc"),
            )
            result = await self._service.list_books(query)
            return library_pb2.ListBooksResponse(
                books=[_book_to_proto(b) for b in result.items],
                next_page_token=result.continuation_token or "",
            )

    async def GetBook(self, request, context):
        with _tracer.start_as_current_span("grpc.GetBook"):
            book = await self._service.get_book(uuid.UUID(request.book_id))
            if not book:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Book not found")
            return _book_to_proto(book)

    async def CreateBook(self, request, context):
        with _tracer.start_as_current_span("grpc.CreateBook"):
            if request.idempotency_key:
                logger.debug("CreateBook idempotency_key=%s", request.idempotency_key)
            try:
                data = BookCreate(
                    isbn=request.isbn,
                    title=request.title,
                    author=request.author,
                    genre=request.genre,
                    published_year=request.published_year,
                    total_copies=request.total_copies,
                )
                book = await self._service.create_book(data)
                return _book_to_proto(book)
            except DuplicateISBNError as e:
                await context.abort(grpc.StatusCode.ALREADY_EXISTS, str(e))

    async def UpdateBook(self, request, context):
        with _tracer.start_as_current_span("grpc.UpdateBook"):
            try:
                update_kwargs = _build_update_kwargs(request)
                data = BookUpdate(**update_kwargs)
                expected_version = request.expected_version if request.expected_version else None
                book = await self._service.update_book(
                    uuid.UUID(request.book_id), data, expected_version=expected_version
                )
                if not book:
                    await context.abort(grpc.StatusCode.NOT_FOUND, "Book not found")
                return _book_to_proto(book)
            except DuplicateISBNError as e:
                await context.abort(grpc.StatusCode.ALREADY_EXISTS, str(e))
            except StaleVersionError:
                await context.abort(grpc.StatusCode.ABORTED, "Version mismatch")

    async def DeleteBook(self, request, context):
        with _tracer.start_as_current_span("grpc.DeleteBook"):
            try:
                deleted = await self._service.delete_book(uuid.UUID(request.book_id))
                if not deleted:
                    await context.abort(grpc.StatusCode.NOT_FOUND, "Book not found")
                return library_pb2.DeleteBookResponse()
            except ActiveReservationsError:
                await context.abort(
                    grpc.StatusCode.FAILED_PRECONDITION,
                    "Cannot delete book with active reservations",
                )

    async def ReserveBooks(self, request, context):
        with _tracer.start_as_current_span("grpc.ReserveBooks"):
            if request.idempotency_key:
                logger.debug("ReserveBooks idempotency_key=%s", request.idempotency_key)
            try:
                data = ReservationCreate(
                    user_id=uuid.UUID(request.user_id),
                    book_ids=[uuid.UUID(bid) for bid in request.book_ids],
                )
                reservations = await self._service.reserve_books(data)
                return library_pb2.ReserveBooksResponse(
                    reservations=[_reservation_to_proto(r) for r in reservations]
                )
            except ValueError as e:
                await context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))

    async def ReturnReservation(self, request, context):
        with _tracer.start_as_current_span("grpc.ReturnReservation"):
            try:
                reservation = await self._service.return_reservation(
                    uuid.UUID(request.reservation_id)
                )
                if not reservation:
                    await context.abort(grpc.StatusCode.NOT_FOUND, "Reservation not found")
                return _reservation_to_proto(reservation)
            except ValueError as e:
                await context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))

    async def ListReservations(self, request, _context):
        with _tracer.start_as_current_span("grpc.ListReservations"):
            query = ListReservationsQuery(
                user_id=uuid.UUID(request.user_id) if request.user_id else None,
                status=_RESERVATION_STATUS_PROTO_TO_STRING.get(request.status),
                book_id=uuid.UUID(request.book_id) if request.book_id else None,
                limit=request.page_size or 20,
                continuation_token=request.page_token or None,
                sort_by=_RESERVATION_SORT_FIELD_MAP.get(request.sort_by, "reserved_at"),
                sort_order=_SORT_ORDER_MAP.get(request.sort_order, "asc"),
            )
            result = await self._service.list_reservations(query)
            return library_pb2.ListReservationsResponse(
                reservations=[_reservation_to_proto(r) for r in result.items],
                next_page_token=result.continuation_token or "",
            )

    async def GetReservation(self, request, context):
        with _tracer.start_as_current_span("grpc.GetReservation"):
            reservation = await self._service.get_reservation(uuid.UUID(request.reservation_id))
            if not reservation:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Reservation not found")
            return _reservation_to_proto(reservation)


async def start_grpc_server(book_service: BookService, port: int = 50051):
    server = aio.server()

    servicer = LibraryServiceServicer(book_service)
    library_pb2_grpc.add_LibraryServiceServicer_to_server(servicer, server)

    health_servicer = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set("library.v1.LibraryService", health_pb2.HealthCheckResponse.SERVING)

    from grpc_reflection.v1alpha import reflection

    service_names = (
        library_pb2.DESCRIPTOR.services_by_name["LibraryService"].full_name,
        health_pb2.DESCRIPTOR.services_by_name["Health"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(service_names, server)

    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    logger.info("gRPC server started on port %d", port)
    return server
