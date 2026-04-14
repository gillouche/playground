import json
import logging
import re

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("api-lab.idempotency")

DEFAULT_TTL = 86400
_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)


class IdempotencyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_client=None, redis_client_ref=None, ttl: int = DEFAULT_TTL):
        super().__init__(app)
        self._redis_client = redis_client
        self._redis_client_ref = redis_client_ref
        self.ttl = ttl

    @property
    def redis_client(self):
        if self._redis_client is not None:
            return self._redis_client
        if self._redis_client_ref:
            return self._redis_client_ref[0]
        return None

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:  # noqa: PLR0911
        if request.method != "POST":
            return await call_next(request)

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return await call_next(request)

        if self.redis_client is None:
            return await call_next(request)

        if not _UUID_PATTERN.match(idempotency_key):
            from starlette.responses import JSONResponse

            return JSONResponse(
                status_code=400,
                content={"detail": "Idempotency-Key must be a valid UUID"},
            )

        cache_key = f"idempotency:{request.method}:{request.url.path}:{idempotency_key}"

        try:
            cached = await self.redis_client.get(cache_key)
        except Exception:
            logger.debug("Redis read failed for idempotency check, allowing request through")
            return await call_next(request)

        if cached:
            data = json.loads(cached)
            return Response(
                content=data["body"],
                status_code=data["status_code"],
                headers=data["headers"],
            )

        response = await call_next(request)

        body = b""
        async for chunk in response.body_iterator:
            if isinstance(chunk, str):
                body += chunk.encode("utf-8")
            else:
                body += chunk

        cache_data = json.dumps(
            {
                "status_code": response.status_code,
                "body": body.decode("utf-8"),
                "headers": dict(response.headers),
            }
        )

        try:
            await self.redis_client.set(cache_key, cache_data, ex=self.ttl)
        except Exception:
            logger.debug("Redis write failed for idempotency cache, continuing without caching")

        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
        )
