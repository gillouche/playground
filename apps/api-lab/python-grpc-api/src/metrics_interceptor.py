import time

import grpc
from prometheus_client import Counter, Histogram

grpc_server_handled_total = Counter(
    "grpc_server_handled_total", "gRPC requests handled", ["method", "code"]
)
grpc_server_handling_seconds = Histogram(
    "grpc_server_handling_seconds", "gRPC request latency", ["method"]
)


class MetricsInterceptor(grpc.aio.ServerInterceptor):
    async def intercept_service(self, continuation, handler_call_details):
        method = handler_call_details.method
        start = time.perf_counter()
        try:
            handler = await continuation(handler_call_details)
            grpc_server_handled_total.labels(method=method, code="OK").inc()
            return handler
        except Exception:
            grpc_server_handled_total.labels(method=method, code="ERROR").inc()
            raise
        finally:
            duration = time.perf_counter() - start
            grpc_server_handling_seconds.labels(method=method).observe(duration)
