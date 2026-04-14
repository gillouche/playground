from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

DEPRECATED_VERSIONS: dict[str, str] = {}


class SunsetMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        path = request.url.path
        for prefix, sunset_date in DEPRECATED_VERSIONS.items():
            if path.startswith(prefix):
                response.headers["Sunset"] = sunset_date
                response.headers["Deprecation"] = "true"
                break
        return response
