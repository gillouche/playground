import json
import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("api-lab.idempotency")

DEFAULT_TTL = 86400


class IdempotencyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_client, ttl: int = DEFAULT_TTL):
        super().__init__(app)
        self.redis_client = redis_client
        self.ttl = ttl

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method != "POST":
            return await call_next(request)

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return await call_next(request)

        cache_key = f"idempotency:{idempotency_key}"

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
