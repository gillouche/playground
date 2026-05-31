import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_client():
    from client import LibraryClient

    return AsyncMock(spec=LibraryClient)


@pytest.fixture
def client_with_mock(mock_client):
    import schema as schema_module
    from main import app

    original = schema_module._client
    schema_module._client = mock_client
    yield app, mock_client
    schema_module._client = original


def _sample_book():
    return {
        "id": str(uuid.uuid4()),
        "isbn": "9780134685991",
        "title": "Effective Java",
        "author": "Joshua Bloch",
        "genre": "Programming",
        "published_year": 2018,
        "total_copies": 5,
        "available_copies": 5,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }


class TestGraphQLGateway:
    async def test_healthz(self):
        from main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/healthz")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

    async def test_list_books(self, client_with_mock):
        app, mock = client_with_mock
        book = _sample_book()
        mock.list_books.return_value = {
            "items": [book],
            "continuation_token": None,
            "has_more": False,
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/graphql",
                json={"query": "{ books { items { isbn title } continuationToken hasMore } }"},
            )
            assert response.status_code == 200
            data = response.json()["data"]["books"]
            assert len(data["items"]) == 1
            assert data["items"][0]["isbn"] == "9780134685991"
            assert data["continuationToken"] is None
            assert data["hasMore"] is False

    async def test_list_books_with_pagination(self, client_with_mock):
        app, mock = client_with_mock
        mock.list_books.return_value = {
            "items": [],
            "continuation_token": "next_token",
            "has_more": True,
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/graphql",
                json={
                    "query": """
                    {
                        books(limit: 5, continuationToken: "prev_token") {
                            items { isbn }
                            continuationToken
                            hasMore
                        }
                    }
                    """
                },
            )
            assert response.status_code == 200
            data = response.json()["data"]["books"]
            assert data["continuationToken"] == "next_token"
            assert data["hasMore"] is True
            mock.list_books.assert_called_once()
            call_args = mock.list_books.call_args[0]
            params = call_args[0]
            assert params.limit == 5
            assert params.continuation_token == "prev_token"

    async def test_create_book_mutation(self, client_with_mock):
        app, mock = client_with_mock
        mock.create_book.return_value = _sample_book()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/graphql",
                json={
                    "query": """
                    mutation {
                        createBook(
                            isbn: "9780134685991"
                            title: "Effective Java"
                            author: "Joshua Bloch"
                            genre: "Programming"
                            publishedYear: 2018
                            totalCopies: 5
                        ) {
                            isbn
                            title
                        }
                    }
                    """
                },
            )
            assert response.status_code == 200
            data = response.json()["data"]["createBook"]
            assert data["isbn"] == "9780134685991"

    async def test_introspection(self):
        from main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/graphql",
                json={"query": "{ __typename }"},
            )
            assert response.status_code == 200
            assert "data" in response.json()
