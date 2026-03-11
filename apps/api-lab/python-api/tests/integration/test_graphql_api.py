from httpx import ASGITransport, AsyncClient


class TestGraphQLEndpoint:
    async def test_graphql_introspection(self):
        """Test that GraphQL endpoint responds to introspection."""
        from main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/graphql",
                json={"query": "{ __typename }"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
