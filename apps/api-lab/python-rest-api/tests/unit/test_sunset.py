from httpx import ASGITransport, AsyncClient
from middleware.sunset import DEPRECATED_VERSIONS, SunsetMiddleware
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route


def _create_app():
    async def handler(_request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/api/v1/test", handler), Route("/api/v2/test", handler)])
    app.add_middleware(SunsetMiddleware)
    return app


class TestSunsetMiddleware:
    async def test_no_sunset_when_not_deprecated(self):
        async with AsyncClient(
            transport=ASGITransport(app=_create_app()), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/test")
            assert response.status_code == 200
            assert "Sunset" not in response.headers

    async def test_sunset_header_when_deprecated(self):
        DEPRECATED_VERSIONS["/api/v1"] = "Sat, 01 Jan 2028 00:00:00 GMT"
        try:
            async with AsyncClient(
                transport=ASGITransport(app=_create_app()), base_url="http://test"
            ) as client:
                response = await client.get("/api/v1/test")
                assert response.headers["Sunset"] == "Sat, 01 Jan 2028 00:00:00 GMT"
                assert response.headers["Deprecation"] == "true"
        finally:
            DEPRECATED_VERSIONS.clear()

    async def test_non_deprecated_version_unaffected(self):
        DEPRECATED_VERSIONS["/api/v1"] = "Sat, 01 Jan 2028 00:00:00 GMT"
        try:
            async with AsyncClient(
                transport=ASGITransport(app=_create_app()), base_url="http://test"
            ) as client:
                response = await client.get("/api/v2/test")
                assert "Sunset" not in response.headers
        finally:
            DEPRECATED_VERSIONS.clear()
