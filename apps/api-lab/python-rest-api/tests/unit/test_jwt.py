import time
import uuid

import jwt as pyjwt
import pytest
from auth.jwt import InvalidTokenError, JWTValidator
from auth.models import AuthenticatedUser
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

ISSUER = "http://localhost:8180/realms/api-lab"
AUDIENCE = "api-lab"


def _generate_rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    public_key = private_key.public_key()
    return private_pem, public_key


def _encode_token(private_pem, payload):
    return pyjwt.encode(payload, private_pem, algorithm="RS256")


@pytest.fixture()
def rsa_keys():
    return _generate_rsa_keypair()


def _make_payload(**overrides):
    defaults = {
        "sub": str(uuid.uuid4()),
        "preferred_username": "testuser",
        "email": "test@example.com",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
        "realm_access": {"roles": ["user"]},
    }
    defaults.update(overrides)
    return defaults


def _create_validator_with_key(public_key):
    validator = JWTValidator.__new__(JWTValidator)
    validator._jwks_client = None
    validator._issuer = ISSUER
    validator._audience = AUDIENCE
    validator._public_keys = {"default": public_key}
    return validator


class TestJWTValidator:
    async def test_valid_token_returns_authenticated_user(self, rsa_keys):
        private_pem, public_key = rsa_keys
        sub = str(uuid.uuid4())
        payload = _make_payload(
            sub=sub,
            preferred_username="alice",
            email="alice@example.com",
            realm_access={"roles": ["user", "editor"]},
        )
        token = _encode_token(private_pem, payload)
        validator = _create_validator_with_key(public_key)

        user = await validator.validate(token)

        assert isinstance(user, AuthenticatedUser)
        assert user.sub == uuid.UUID(sub)
        assert user.username == "alice"
        assert user.email == "alice@example.com"
        assert user.roles == ["user", "editor"]

    async def test_expired_token_raises_invalid_token_error(self, rsa_keys):
        private_pem, public_key = rsa_keys
        payload = _make_payload(exp=int(time.time()) - 3600)
        token = _encode_token(private_pem, payload)
        validator = _create_validator_with_key(public_key)

        with pytest.raises(InvalidTokenError) as exc_info:
            await validator.validate(token)
        assert exc_info.value.reason == "expired"

    async def test_wrong_issuer_raises_invalid_token_error(self, rsa_keys):
        private_pem, public_key = rsa_keys
        payload = _make_payload(iss="http://wrong-issuer/realms/other")
        token = _encode_token(private_pem, payload)
        validator = _create_validator_with_key(public_key)

        with pytest.raises(InvalidTokenError) as exc_info:
            await validator.validate(token)
        assert exc_info.value.reason == "invalid_issuer"

    async def test_missing_sub_raises_invalid_token_error(self, rsa_keys):
        private_pem, public_key = rsa_keys
        payload = _make_payload()
        del payload["sub"]
        token = _encode_token(private_pem, payload)
        validator = _create_validator_with_key(public_key)

        with pytest.raises(InvalidTokenError) as exc_info:
            await validator.validate(token)
        assert exc_info.value.reason == "missing_sub"

    async def test_admin_role_extracted_from_realm_access(self, rsa_keys):
        private_pem, public_key = rsa_keys
        payload = _make_payload(realm_access={"roles": ["user", "admin"]})
        token = _encode_token(private_pem, payload)
        validator = _create_validator_with_key(public_key)

        user = await validator.validate(token)

        assert "admin" in user.roles
        assert user.is_admin is True

    async def test_wrong_audience_raises_invalid_token_error(self, rsa_keys):
        private_pem, public_key = rsa_keys
        payload = _make_payload(aud="wrong-audience")
        token = _encode_token(private_pem, payload)
        validator = _create_validator_with_key(public_key)

        with pytest.raises(InvalidTokenError) as exc_info:
            await validator.validate(token)
        assert exc_info.value.reason == "invalid_audience"

    async def test_wrong_signing_key_raises_invalid_token_error(self, rsa_keys):
        other_private_pem, _ = _generate_rsa_keypair()
        _, public_key = rsa_keys
        payload = _make_payload()
        token = _encode_token(other_private_pem, payload)
        validator = _create_validator_with_key(public_key)

        with pytest.raises(InvalidTokenError) as exc_info:
            await validator.validate(token)
        assert exc_info.value.reason == "invalid_signature"

    async def test_no_realm_access_returns_empty_roles(self, rsa_keys):
        private_pem, public_key = rsa_keys
        payload = _make_payload()
        del payload["realm_access"]
        token = _encode_token(private_pem, payload)
        validator = _create_validator_with_key(public_key)

        user = await validator.validate(token)

        assert user.roles == []
        assert user.is_admin is False
