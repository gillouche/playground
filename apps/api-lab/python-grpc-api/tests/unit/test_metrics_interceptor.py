from unittest.mock import AsyncMock, MagicMock

import pytest
from metrics_interceptor import (
    MetricsInterceptor,
    grpc_server_handled_total,
    grpc_server_handling_seconds,
)


@pytest.fixture
def interceptor():
    return MetricsInterceptor()


def _make_handler_call_details(method="/library.v1.LibraryService/ListBooks"):
    details = MagicMock()
    details.method = method
    return details


class TestMetricsInterceptor:
    async def test_increments_ok_counter_on_success(self, interceptor):
        handler = MagicMock()
        continuation = AsyncMock(return_value=handler)
        details = _make_handler_call_details()

        before = grpc_server_handled_total.labels(method=details.method, code="OK")._value.get()
        result = await interceptor.intercept_service(continuation, details)
        after = grpc_server_handled_total.labels(method=details.method, code="OK")._value.get()

        assert result is handler
        assert after == before + 1

    async def test_increments_error_counter_on_exception(self, interceptor):
        continuation = AsyncMock(side_effect=RuntimeError("boom"))
        details = _make_handler_call_details("/library.v1.LibraryService/GetBook")

        before = grpc_server_handled_total.labels(method=details.method, code="ERROR")._value.get()
        with pytest.raises(RuntimeError, match="boom"):
            await interceptor.intercept_service(continuation, details)
        after = grpc_server_handled_total.labels(method=details.method, code="ERROR")._value.get()

        assert after == before + 1

    async def test_observes_latency_on_success(self, interceptor):
        continuation = AsyncMock(return_value=MagicMock())
        details = _make_handler_call_details("/library.v1.LibraryService/CreateBook")

        before = grpc_server_handling_seconds.labels(method=details.method)._sum.get()
        await interceptor.intercept_service(continuation, details)
        after = grpc_server_handling_seconds.labels(method=details.method)._sum.get()

        assert after > before

    async def test_observes_latency_on_error(self, interceptor):
        continuation = AsyncMock(side_effect=ValueError("fail"))
        details = _make_handler_call_details("/library.v1.LibraryService/DeleteBook")

        before = grpc_server_handling_seconds.labels(method=details.method)._sum.get()
        with pytest.raises(ValueError):
            await interceptor.intercept_service(continuation, details)
        after = grpc_server_handling_seconds.labels(method=details.method)._sum.get()

        assert after > before
