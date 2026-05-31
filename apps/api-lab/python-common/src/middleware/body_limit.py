from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

DEFAULT_MAX_BODY_SIZE = 1_048_576


class BodyLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_size: int = DEFAULT_MAX_BODY_SIZE):
        super().__init__(app)
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_size:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large", "status_code": 413},
            )
        return await call_next(request)
