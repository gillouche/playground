import ipaddress
import logging
import os
import time

from observability.metrics import rate_limit_rejections_total
from observability.security_events import log_rate_limit
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("api-lab.rate_limit")

RATE_TIERS = {
    "exempt": None,
    "auth": (10, 60),
    "write": (50, 60),
    "read": (200, 60),
}

EXEMPT_PATHS = {"/healthz", "/ready", "/metrics"}

AUTH_PATHS = {"/api/v1/auth/login", "/api/v1/auth/register"}


def _get_client_ip(request: Request) -> str:
    trusted_proxies_str = os.environ.get(
        "TRUSTED_PROXIES", "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
    )
    trusted_networks = [
        ipaddress.ip_network(cidr.strip())
        for cidr in trusted_proxies_str.split(",")
        if cidr.strip()
    ]

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ips = [ip.strip() for ip in forwarded_for.split(",")]
        for ip in reversed(ips):
            try:
                addr = ipaddress.ip_address(ip)
                if not any(addr in net for net in trusted_networks):
                    return str(ip)
            except ValueError:
                continue

    return request.client.host if request.client else "unknown"


def _get_tier(request: Request) -> str:
    path = request.url.path
    if path in EXEMPT_PATHS:
        return "exempt"
    if path in AUTH_PATHS:
        return "auth"
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        return "write"
    return "read"


def _get_rate_key(request: Request, tier: str) -> str:
    client_ip = _get_client_ip(request)
    return f"rate_limit:{client_ip}:{tier}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_client=None, redis_client_ref=None):
        super().__init__(app)
        self._redis_client = redis_client
        self._redis_client_ref = redis_client_ref

    @property
    def redis_client(self):
        if self._redis_client is not None:
            return self._redis_client
        if self._redis_client_ref:
            return self._redis_client_ref[0]
        return None

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        tier = _get_tier(request)

        if tier == "exempt":
            return await call_next(request)

        if self.redis_client is None:
            return await call_next(request)

        limits = RATE_TIERS[tier]
        assert limits is not None
        rate_limit, window_seconds = limits

        key = _get_rate_key(request, tier)
        current_window = int(time.time()) // window_seconds
        redis_key = f"{key}:{current_window}"
        window_reset = (current_window + 1) * window_seconds

        try:
            current_count = await self.redis_client.incr(redis_key)
            if current_count == 1:
                await self.redis_client.expire(redis_key, window_seconds)

            remaining = max(0, rate_limit - current_count)

            if current_count > rate_limit:
                client_ip = _get_client_ip(request)
                log_rate_limit(
                    ip=client_ip,
                    user_id=None,
                    endpoint=str(request.url.path),
                    tier=tier,
                    count=current_count,
                )
                rate_limit_rejections_total.labels(endpoint=str(request.url.path), tier=tier).inc()
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded", "status_code": 429},
                    headers={
                        "X-RateLimit-Limit": str(rate_limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(window_reset),
                        "Retry-After": str(window_reset - int(time.time())),
                    },
                )

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(rate_limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(window_reset)
            return response

        except Exception:
            logger.debug("Redis unavailable for rate limiting, allowing request through")
            return await call_next(request)
