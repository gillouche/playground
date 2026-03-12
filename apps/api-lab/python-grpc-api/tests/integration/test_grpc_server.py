from unittest.mock import AsyncMock

from grpc_server import SERVICE_NAME, LibraryServiceHandler


class TestGrpcHandler:
    def test_handler_registers_all_methods(self):
        service = AsyncMock()
        handler = LibraryServiceHandler(service)
        expected_methods = [
            "ListBooks",
            "GetBook",
            "CreateBook",
            "UpdateBook",
            "DeleteBook",
            "GetInventory",
            "ReserveBooks",
            "ReturnReservation",
            "ListReservations",
            "GetReservation",
        ]
        for method in expected_methods:
            from unittest.mock import MagicMock

            details = MagicMock()
            details.method = f"/{SERVICE_NAME}/{method}"
            assert handler.service(details) is not None, f"Missing handler for {method}"
