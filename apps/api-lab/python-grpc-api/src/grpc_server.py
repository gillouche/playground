import logging
import uuid

import grpc
from generated.models import BookCreate, BookUpdate, ReservationCreate
from grpc import aio
from services.book_service import BookService

logger = logging.getLogger("api-lab.grpc")

# Without generated proto stubs, we implement a generic gRPC handler that
# dispatches based on method name. Once Bazel proto_library + grpc_py_library
# targets are configured, replace this with proper pb2_grpc registration.

SERVICE_NAME = "library.v1.LibraryService"

# Method name -> handler mapping (populated in LibraryServiceHandler.__init__)


class LibraryServiceHandler(grpc.GenericRpcHandler):
    """Generic gRPC handler wrapping BookService.

    This is used until proper protobuf stubs are generated via Bazel.
    Each method serializes responses as JSON bytes.
    """

    def __init__(self, book_service: BookService):
        self._service = book_service
        self._methods = {
            f"/{SERVICE_NAME}/ListBooks": grpc.unary_unary_rpc_method_handler(self._list_books),
            f"/{SERVICE_NAME}/GetBook": grpc.unary_unary_rpc_method_handler(self._get_book),
            f"/{SERVICE_NAME}/CreateBook": grpc.unary_unary_rpc_method_handler(self._create_book),
            f"/{SERVICE_NAME}/UpdateBook": grpc.unary_unary_rpc_method_handler(self._update_book),
            f"/{SERVICE_NAME}/DeleteBook": grpc.unary_unary_rpc_method_handler(self._delete_book),
            f"/{SERVICE_NAME}/GetInventory": grpc.unary_unary_rpc_method_handler(
                self._get_inventory
            ),
            f"/{SERVICE_NAME}/ReserveBooks": grpc.unary_unary_rpc_method_handler(
                self._reserve_books
            ),
            f"/{SERVICE_NAME}/ReturnReservation": grpc.unary_unary_rpc_method_handler(
                self._return_reservation
            ),
            f"/{SERVICE_NAME}/ListReservations": grpc.unary_unary_rpc_method_handler(
                self._list_reservations
            ),
            f"/{SERVICE_NAME}/GetReservation": grpc.unary_unary_rpc_method_handler(
                self._get_reservation
            ),
        }

    def service(self, handler_call_details):
        return self._methods.get(handler_call_details.method)

    # -- JSON serialization helpers --

    @staticmethod
    def _serialize(data) -> bytes:
        import json

        return json.dumps(data, default=str).encode("utf-8")

    @staticmethod
    def _deserialize(data: bytes) -> dict:
        import json

        return json.loads(data) if data else {}

    @staticmethod
    def _book_to_dict(book):
        return {
            "id": str(book.id),
            "isbn": book.isbn,
            "title": book.title,
            "author": book.author,
            "genre": book.genre,
            "published_year": book.published_year,
            "total_copies": book.total_copies,
            "available_copies": book.available_copies,
            "created_at": str(book.created_at),
            "updated_at": str(book.updated_at),
        }

    @staticmethod
    def _reservation_to_dict(reservation):
        return {
            "id": str(reservation.id),
            "book_id": str(reservation.book_id),
            "user_id": reservation.user_id,
            "reserved_at": str(reservation.reserved_at),
            "due_date": str(reservation.due_date),
            "returned_at": str(reservation.returned_at) if reservation.returned_at else None,
            "status": reservation.status
            if isinstance(reservation.status, str)
            else reservation.status.value,
        }

    # -- RPC method implementations --

    async def _list_books(self, request, _context):
        req = self._deserialize(request)
        books = await self._service.list_books(
            available_only=req.get("available_only", False),
            genre=req.get("genre"),
            author=req.get("author"),
            search=req.get("search"),
        )
        return self._serialize({"books": [self._book_to_dict(b) for b in books]})

    async def _get_book(self, request, context):
        req = self._deserialize(request)
        book = await self._service.get_book(uuid.UUID(req["book_id"]))
        if not book:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Book not found")
        return self._serialize(self._book_to_dict(book))

    async def _create_book(self, request, _context):
        req = self._deserialize(request)
        data = BookCreate(
            isbn=req["isbn"],
            title=req["title"],
            author=req["author"],
            genre=req["genre"],
            published_year=req["published_year"],
            total_copies=req["total_copies"],
        )
        book = await self._service.create_book(data)
        return self._serialize(self._book_to_dict(book))

    async def _update_book(self, request, context):
        req = self._deserialize(request)
        book_id = uuid.UUID(req.pop("book_id"))
        data = BookUpdate(**{k: v for k, v in req.items() if v is not None})
        book = await self._service.update_book(book_id, data)
        if not book:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Book not found")
        return self._serialize(self._book_to_dict(book))

    async def _delete_book(self, request, context):
        req = self._deserialize(request)
        deleted = await self._service.delete_book(uuid.UUID(req["book_id"]))
        if not deleted:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Book not found")
        return self._serialize({"deleted": True})

    async def _get_inventory(self, _request, _context):
        books = await self._service.get_inventory()
        return self._serialize({"books": [self._book_to_dict(b) for b in books]})

    async def _reserve_books(self, request, context):
        req = self._deserialize(request)
        try:
            data = ReservationCreate(
                user_id=req["user_id"],
                book_ids=[uuid.UUID(bid) for bid in req["book_ids"]],
            )
            reservations = await self._service.reserve_books(data)
            return self._serialize(
                {"reservations": [self._reservation_to_dict(r) for r in reservations]}
            )
        except ValueError as e:
            await context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))

    async def _return_reservation(self, request, context):
        req = self._deserialize(request)
        try:
            reservation = await self._service.return_reservation(uuid.UUID(req["reservation_id"]))
            if not reservation:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Reservation not found")
            return self._serialize(self._reservation_to_dict(reservation))
        except ValueError as e:
            await context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))

    async def _list_reservations(self, request, _context):
        req = self._deserialize(request)
        reservations = await self._service.list_reservations(
            user_id=req.get("user_id"),
            status=req.get("status"),
            book_id=uuid.UUID(req["book_id"]) if req.get("book_id") else None,
        )
        return self._serialize(
            {"reservations": [self._reservation_to_dict(r) for r in reservations]}
        )

    async def _get_reservation(self, request, context):
        req = self._deserialize(request)
        reservation = await self._service.get_reservation(uuid.UUID(req["reservation_id"]))
        if not reservation:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Reservation not found")
        return self._serialize(self._reservation_to_dict(reservation))


async def start_grpc_server(book_service: BookService, port: int = 50051):
    """Start gRPC server with generic JSON-based handler."""
    server = aio.server()
    handler = LibraryServiceHandler(book_service)
    server.add_generic_rpc_handlers([handler])

    from grpc_reflection.v1alpha import reflection

    SERVICE_NAMES = (SERVICE_NAME,)
    reflection.enable_server_reflection(SERVICE_NAMES, server)

    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    logger.info("gRPC server started on port %d", port)
    return server
