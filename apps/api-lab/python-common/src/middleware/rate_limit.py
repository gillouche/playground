import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("api-lab.rate_limit")


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_client, rate_limit: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.redis_client = redis_client
        self.rate_limit = rate_limit
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        current_window = int(time.time()) // self.window_seconds
        key = f"rate_limit:{client_ip}:{current_window}"
        window_reset = (current_window + 1) * self.window_seconds

        try:
            current_count = await self.redis_client.incr(key)
            if current_count == 1:
                await self.redis_client.expire(key, self.window_seconds)

            remaining = max(0, self.rate_limit - current_count)

            if current_count > self.rate_limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded", "status_code": 429},
                    headers={
                        "X-RateLimit-Limit": str(self.rate_limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(window_reset),
                        "Retry-After": str(window_reset - int(time.time())),
                    },
                )

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(window_reset)
            return response

        except Exception:
            logger.debug("Redis unavailable for rate limiting, allowing request through")
            return await call_next(request)
