import uuid


class TestRegistrationAndLogin:
    async def test_register_login_access_api(
        self, _auth_client, rest_client, _registered_user, user_token
    ):
        headers = {"Authorization": f"Bearer {user_token}"}
        resp = await rest_client.get("/api/v1/books", headers=headers)
        assert resp.status_code == 200

    async def test_user_cannot_create_book(self, rest_client, user_token):
        headers = {"Authorization": f"Bearer {user_token}"}
        resp = await rest_client.post(
            "/api/v1/books",
            json={
                "isbn": "9780134685991",
                "title": "Test Book",
                "author": "Author",
                "genre": "Fiction",
                "published_year": 2020,
                "total_copies": 5,
            },
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_admin_can_create_book(self, rest_client, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = await rest_client.post(
            "/api/v1/books",
            json={
                "isbn": f"{9780000000000 + uuid.uuid4().int % 999}",
                "title": "Admin Book",
                "author": "Admin Author",
                "genre": "Programming",
                "published_year": 2024,
                "total_copies": 3,
            },
            headers=headers,
        )
        assert resp.status_code == 201


class TestReservationIsolation:
    async def test_user_only_sees_own_reservations(self, auth_client, rest_client, admin_token):
        user1_name = f"patron1-{uuid.uuid4().hex[:8]}"
        user2_name = f"patron2-{uuid.uuid4().hex[:8]}"

        await auth_client.post(
            "/api/v1/auth/register",
            json={
                "username": user1_name,
                "email": f"{user1_name}@test.local",
                "password": "testpass123",
            },
        )
        await auth_client.post(
            "/api/v1/auth/register",
            json={
                "username": user2_name,
                "email": f"{user2_name}@test.local",
                "password": "testpass123",
            },
        )

        u1_resp = await auth_client.post(
            "/api/v1/auth/login", json={"username": user1_name, "password": "testpass123"}
        )
        u2_resp = await auth_client.post(
            "/api/v1/auth/login", json={"username": user2_name, "password": "testpass123"}
        )
        u1_token = u1_resp.json()["access_token"]
        u2_token = u2_resp.json()["access_token"]

        book_resp = await rest_client.post(
            "/api/v1/books",
            json={
                "isbn": f"{9780000000000 + uuid.uuid4().int % 999}",
                "title": "Shared Book",
                "author": "Author",
                "genre": "Fiction",
                "published_year": 2024,
                "total_copies": 5,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        book_id = book_resp.json()["id"]

        await rest_client.post(
            "/api/v1/reservations",
            json={"book_ids": [book_id]},
            headers={"Authorization": f"Bearer {u1_token}"},
        )

        u1_reservations = await rest_client.get(
            "/api/v1/reservations", headers={"Authorization": f"Bearer {u1_token}"}
        )
        u2_reservations = await rest_client.get(
            "/api/v1/reservations", headers={"Authorization": f"Bearer {u2_token}"}
        )

        assert len(u1_reservations.json()["items"]) >= 1
        assert len(u2_reservations.json()["items"]) == 0


class TestTokenRefresh:
    async def test_refresh_flow(self, auth_client, rest_client, registered_user):
        login_resp = await auth_client.post(
            "/api/v1/auth/login",
            json={
                "username": registered_user["username"],
                "password": registered_user["password"],
            },
        )
        tokens = login_resp.json()
        refresh_resp = await auth_client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": tokens["refresh_token"],
            },
        )
        assert refresh_resp.status_code == 200
        new_token = refresh_resp.json()["access_token"]
        books_resp = await rest_client.get(
            "/api/v1/books", headers={"Authorization": f"Bearer {new_token}"}
        )
        assert books_resp.status_code == 200
