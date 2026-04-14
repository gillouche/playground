import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from auth.models import AuthenticatedUser

anyio_backend = "asyncio"


@pytest.fixture
def mock_jwt_validator():
    return AsyncMock()


@pytest.fixture
def interceptor(mock_jwt_validator):
    from auth_interceptor import AuthInterceptor

    return AuthInterceptor(mock_jwt_validator)


def _make_handler_call_details(method="/library.v1.LibraryService/ListBooks", metadata=None):
    details = MagicMock()
    details.method = method
    details.invocation_metadata = metadata or {}
    return details


def _make_continuation():
    handler = AsyncMock()
    return handler


class TestAuthInterceptorSkipsExemptMethods:
    @pytest.mark.asyncio
    async def test_skips_health_check(self, interceptor):
        details = _make_handler_call_details(method="/grpc.health.v1.Health/Check")
        continuation = _make_continuation()

        await interceptor.intercept_service(continuation, details)

        continuation.assert_awaited_once_with(details)

    @pytest.mark.asyncio
    async def test_skips_health_watch(self, interceptor):
        details = _make_handler_call_details(method="/grpc.health.v1.Health/Watch")
        continuation = _make_continuation()

        await interceptor.intercept_service(continuation, details)

        continuation.assert_awaited_once_with(details)

    @pytest.mark.asyncio
    async def test_skips_reflection(self, interceptor):
        details = _make_handler_call_details(
            method="/grpc.reflection.v1alpha.ServerReflection/ServerReflectionInfo"
        )
        continuation = _make_continuation()

        await interceptor.intercept_service(continuation, details)

        continuation.assert_awaited_once_with(details)


class TestAuthInterceptorRejectsUnauthenticated:
    @pytest.mark.asyncio
    async def test_rejects_missing_authorization(self, interceptor):
        details = _make_handler_call_details(metadata={})
        continuation = _make_continuation()

        result = interceptor.intercept_service(continuation, details)
        handler = await result

        continuation.assert_not_awaited()
        assert handler is not None

    @pytest.mark.asyncio
    async def test_rejects_empty_authorization(self, interceptor):
        details = _make_handler_call_details(metadata={"authorization": ""})
        continuation = _make_continuation()

        handler = await interceptor.intercept_service(continuation, details)

        continuation.assert_not_awaited()
        assert handler is not None

    @pytest.mark.asyncio
    async def test_rejects_non_bearer_authorization(self, interceptor):
        details = _make_handler_call_details(metadata={"authorization": "Basic abc123"})
        continuation = _make_continuation()

        handler = await interceptor.intercept_service(continuation, details)

        continuation.assert_not_awaited()
        assert handler is not None

    @pytest.mark.asyncio
    async def test_rejects_invalid_token(self, interceptor, mock_jwt_validator):
        from auth.jwt import InvalidTokenError

        mock_jwt_validator.validate.side_effect = InvalidTokenError("expired")
        details = _make_handler_call_details(metadata={"authorization": "Bearer invalid-token"})
        continuation = _make_continuation()

        handler = await interceptor.intercept_service(continuation, details)

        continuation.assert_not_awaited()
        assert handler is not None


class TestAuthInterceptorAcceptsValidToken:
    @pytest.mark.asyncio
    async def test_valid_token_continues(self, interceptor, mock_jwt_validator):
        user = AuthenticatedUser(
            sub=uuid.uuid4(),
            username="testuser",
            roles=["user"],
            email="test@example.com",
        )
        mock_jwt_validator.validate.return_value = user
        details = _make_handler_call_details(metadata={"authorization": "Bearer valid-token"})
        continuation = _make_continuation()

        await interceptor.intercept_service(continuation, details)

        continuation.assert_awaited_once_with(details)
        mock_jwt_validator.validate.assert_awaited_once_with("valid-token")

    @pytest.mark.asyncio
    async def test_valid_token_stores_user_on_details(self, interceptor, mock_jwt_validator):
        user = AuthenticatedUser(
            sub=uuid.uuid4(),
            username="admin",
            roles=["admin"],
        )
        mock_jwt_validator.validate.return_value = user
        details = _make_handler_call_details(metadata={"authorization": "Bearer admin-token"})
        continuation = _make_continuation()

        await interceptor.intercept_service(continuation, details)

        assert details.user == user

    @pytest.mark.asyncio
    async def test_bearer_case_insensitive(self, interceptor, mock_jwt_validator):
        user = AuthenticatedUser(
            sub=uuid.uuid4(),
            username="testuser",
            roles=[],
        )
        mock_jwt_validator.validate.return_value = user
        details = _make_handler_call_details(metadata={"authorization": "BEARER my-token"})
        continuation = _make_continuation()

        await interceptor.intercept_service(continuation, details)

        continuation.assert_awaited_once()
        mock_jwt_validator.validate.assert_awaited_once_with("my-token")
