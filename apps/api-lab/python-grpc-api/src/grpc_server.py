import logging
import uuid

import grpc
from generated.models import BookCreate, BookUpdate, ReservationCreate
from google.protobuf import timestamp_pb2
from grpc import aio
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from library.v1 import library_pb2, library_pb2_grpc
from observability.tracing import get_tracer
from services.book_service import BookService, DuplicateISBNError

logger = logging.getLogger("api-lab.grpc")

_tracer = get_tracer("api-lab.grpc_server")

_RESERVATION_STATUS_MAP = {
    "ACTIVE": library_pb2.RESERVATION_STATUS_ACTIVE,
    "RETURNED": library_pb2.RESERVATION_STATUS_RETURNED,
    "OVERDUE": library_pb2.RESERVATION_STATUS_OVERDUE,
}


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
        "user_id": reservation.user_id,
        "reserved_at": _datetime_to_timestamp(reservation.reserved_at),
        "due_date": _datetime_to_timestamp(reservation.due_date),
        "status": proto_status,
    }
    if reservation.returned_at is not None:
        kwargs["returned_at"] = _datetime_to_timestamp(reservation.returned_at)
    return library_pb2.Reservation(**kwargs)


class LibraryServiceServicer(library_pb2_grpc.LibraryServiceServicer):
    def __init__(self, book_service: BookService):
        self._service = book_service

    async def ListBooks(self, request, _context):
        with _tracer.start_as_current_span("grpc.ListBooks"):
            books = await self._service.list_books(
                available_only=request.available_only,
                genre=request.genre or None,
                author=request.author or None,
                search=request.search or None,
            )
            return library_pb2.ListBooksResponse(books=[_book_to_proto(b) for b in books])

    async def GetBook(self, request, context):
        with _tracer.start_as_current_span("grpc.GetBook"):
            book = await self._service.get_book(uuid.UUID(request.book_id))
            if not book:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Book not found")
            return _book_to_proto(book)

    async def CreateBook(self, request, context):
        with _tracer.start_as_current_span("grpc.CreateBook"):
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
                update_kwargs = {}
                if request.HasField("isbn"):
                    update_kwargs["isbn"] = request.isbn
                if request.HasField("title"):
                    update_kwargs["title"] = request.title
                if request.HasField("author"):
                    update_kwargs["author"] = request.author
                if request.HasField("genre"):
                    update_kwargs["genre"] = request.genre
                if request.HasField("published_year"):
                    update_kwargs["published_year"] = request.published_year
                if request.HasField("total_copies"):
                    update_kwargs["total_copies"] = request.total_copies
                data = BookUpdate(**update_kwargs)
                book = await self._service.update_book(uuid.UUID(request.book_id), data)
                if not book:
                    await context.abort(grpc.StatusCode.NOT_FOUND, "Book not found")
                return _book_to_proto(book)
            except DuplicateISBNError as e:
                await context.abort(grpc.StatusCode.ALREADY_EXISTS, str(e))

    async def DeleteBook(self, request, context):
        with _tracer.start_as_current_span("grpc.DeleteBook"):
            deleted = await self._service.delete_book(uuid.UUID(request.book_id))
            if not deleted:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Book not found")
            return library_pb2.DeleteBookResponse()

    async def GetInventory(self, _request, _context):
        with _tracer.start_as_current_span("grpc.GetInventory"):
            books = await self._service.get_inventory()
            return library_pb2.GetInventoryResponse(books=[_book_to_proto(b) for b in books])

    async def ReserveBooks(self, request, context):
        with _tracer.start_as_current_span("grpc.ReserveBooks"):
            try:
                data = ReservationCreate(
                    user_id=request.user_id,
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
            reservations = await self._service.list_reservations(
                user_id=request.user_id or None,
                status=request.status or None,
                book_id=uuid.UUID(request.book_id) if request.book_id else None,
            )
            return library_pb2.ListReservationsResponse(
                reservations=[_reservation_to_proto(r) for r in reservations]
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
