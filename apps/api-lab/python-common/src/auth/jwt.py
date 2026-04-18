import logging
import uuid

import jwt
from auth.models import AuthenticatedUser
from config import keycloak_config
from jwt import PyJWKClient

logger = logging.getLogger("api-lab.auth.jwt")


class InvalidTokenError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Invalid token: {reason}")


class JWTValidator:
    def __init__(self):
        self._jwks_client = PyJWKClient(keycloak_config.jwks_url, cache_jwk_set=True, lifespan=300)
        self._issuer = keycloak_config.issuer_url
        self._audience = keycloak_config.client_id
        self._public_keys: dict | None = None

    async def validate(self, token: str) -> AuthenticatedUser:
        try:
            if self._public_keys:
                for key in self._public_keys.values():
                    try:
                        payload = jwt.decode(
                            token,
                            key,
                            algorithms=["RS256"],
                            issuer=self._issuer,
                            audience=self._audience,
                            leeway=2,
                        )
                        break
                    except jwt.InvalidSignatureError:
                        continue
                else:
                    raise InvalidTokenError("invalid_signature")
            else:
                signing_key = self._jwks_client.get_signing_key_from_jwt(token)
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],
                    issuer=self._issuer,
                    audience=self._audience,
                    leeway=2,
                )
        except jwt.ExpiredSignatureError:
            raise InvalidTokenError("expired") from None
        except jwt.InvalidIssuerError:
            raise InvalidTokenError("invalid_issuer") from None
        except jwt.InvalidAudienceError:
            raise InvalidTokenError("invalid_audience") from None
        except jwt.DecodeError:
            raise InvalidTokenError("malformed") from None
        except InvalidTokenError:
            raise
        except Exception as e:
            raise InvalidTokenError(f"validation_failed: {e}") from None

        sub = payload.get("sub")
        if not sub:
            raise InvalidTokenError("missing_sub")

        realm_access = payload.get("realm_access", {})
        roles = realm_access.get("roles", [])

        return AuthenticatedUser(
            sub=uuid.UUID(sub),
            username=payload.get("preferred_username", ""),
            roles=roles,
            email=payload.get("email"),
        )
