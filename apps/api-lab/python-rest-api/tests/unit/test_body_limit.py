from httpx import ASGITransport, AsyncClient
from middleware.body_limit import BodyLimitMiddleware
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route


def _create_app(max_size=1024):
    async def echo(request):
        body = await request.body()
        return PlainTextResponse(f"received {len(body)} bytes")

    app = Starlette(routes=[Route("/", echo, methods=["POST"])])
    app.add_middleware(BodyLimitMiddleware, max_body_size=max_size)
    return app


class TestBodyLimit:
    async def test_allows_small_body(self):
        async with AsyncClient(
            transport=ASGITransport(app=_create_app()), base_url="http://test"
        ) as client:
            response = await client.post("/", content="small", headers={"content-length": "5"})
            assert response.status_code == 200

    async def test_rejects_large_body(self):
        async with AsyncClient(
            transport=ASGITransport(app=_create_app(max_size=10)), base_url="http://test"
        ) as client:
            response = await client.post("/", content="x" * 100, headers={"content-length": "100"})
            assert response.status_code == 413

    async def test_allows_request_without_content_length(self):
        async with AsyncClient(
            transport=ASGITransport(app=_create_app()), base_url="http://test"
        ) as client:
            response = await client.post("/", content="data")
            assert response.status_code == 200
