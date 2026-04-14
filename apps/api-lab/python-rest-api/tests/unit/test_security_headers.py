from httpx import ASGITransport, AsyncClient
from middleware.security_headers import SecurityHeadersMiddleware
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route


def _create_app():
    async def homepage(_request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/", homepage)])
    app.add_middleware(SecurityHeadersMiddleware)
    return app


class TestSecurityHeaders:
    async def test_adds_nosniff(self):
        async with AsyncClient(
            transport=ASGITransport(app=_create_app()), base_url="http://test"
        ) as client:
            response = await client.get("/")
            assert response.headers["X-Content-Type-Options"] == "nosniff"

    async def test_adds_cache_control(self):
        async with AsyncClient(
            transport=ASGITransport(app=_create_app()), base_url="http://test"
        ) as client:
            response = await client.get("/")
            assert response.headers["Cache-Control"] == "no-store"

    async def test_adds_frame_options(self):
        async with AsyncClient(
            transport=ASGITransport(app=_create_app()), base_url="http://test"
        ) as client:
            response = await client.get("/")
            assert response.headers["X-Frame-Options"] == "DENY"

    async def test_adds_referrer_policy(self):
        async with AsyncClient(
            transport=ASGITransport(app=_create_app()), base_url="http://test"
        ) as client:
            response = await client.get("/")
            assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    async def test_adds_permissions_policy(self):
        async with AsyncClient(
            transport=ASGITransport(app=_create_app()), base_url="http://test"
        ) as client:
            response = await client.get("/")
            assert (
                response.headers["Permissions-Policy"] == "geolocation=(), camera=(), microphone=()"
            )
