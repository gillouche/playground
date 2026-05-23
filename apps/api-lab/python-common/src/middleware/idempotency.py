import json
import logging
import re

from config import idempotency_config
from observability.metrics import (
    idempotency_oversize_total,
    idempotency_redis_failures_total,
)
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("api-lab.idempotency")

_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)


class IdempotencyMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        redis_client=None,
        redis_client_ref=None,
        ttl: int | None = None,
        max_body_bytes: int | None = None,
        fail_open: bool | None = None,
    ):
        super().__init__(app)
        self._redis_client = redis_client
        self._redis_client_ref = redis_client_ref
        self.ttl = idempotency_config.ttl if ttl is None else ttl
        self.max_body_bytes = (
            idempotency_config.max_body_bytes if max_body_bytes is None else max_body_bytes
        )
        self.fail_open = idempotency_config.fail_open if fail_open is None else fail_open

    @property
    def redis_client(self):
        if self._redis_client is not None:
            return self._redis_client
        if self._redis_client_ref:
            return self._redis_client_ref[0]
        return None

    def _service_unavailable(self) -> Response:
        return JSONResponse(
            status_code=503,
            content={"detail": "Idempotency service unavailable", "status_code": 503},
            headers={"Retry-After": "5"},
        )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:  # noqa: PLR0911
        if request.method != "POST":
            return await call_next(request)

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return await call_next(request)

        if self.redis_client is None:
            if self.fail_open:
                return await call_next(request)
            return self._service_unavailable()

        if not _UUID_PATTERN.match(idempotency_key):
            return JSONResponse(
                status_code=400,
                content={"detail": "Idempotency-Key must be a valid UUID"},
            )

        cache_key = f"idempotency:{request.method}:{request.url.path}:{idempotency_key}"

        try:
            cached = await self.redis_client.get(cache_key)
        except Exception as e:
            logger.warning("Redis read failed for idempotency check: %s", e)
            idempotency_redis_failures_total.labels(operation="get").inc()
            if self.fail_open:
                return await call_next(request)
            return self._service_unavailable()

        if cached:
            data = json.loads(cached)
            return Response(
                content=data["body"],
                status_code=data["status_code"],
                headers=data["headers"],
            )

        response = await call_next(request)

        body = b""
        oversized = False
        async for chunk in response.body_iterator:
            piece = chunk.encode("utf-8") if isinstance(chunk, str) else chunk
            body += piece
            if len(body) > self.max_body_bytes:
                oversized = True

        if oversized:
            idempotency_oversize_total.inc()
            logger.warning(
                "Idempotency response body %d bytes exceeds max %d; not caching",
                len(body),
                self.max_body_bytes,
            )
        else:
            cache_data = json.dumps(
                {
                    "status_code": response.status_code,
                    "body": body.decode("utf-8"),
                    "headers": dict(response.headers),
                }
            )
            try:
                await self.redis_client.set(cache_key, cache_data, ex=self.ttl)
            except Exception as e:
                logger.warning("Redis write failed for idempotency cache: %s", e)
                idempotency_redis_failures_total.labels(operation="set").inc()

        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
        )
