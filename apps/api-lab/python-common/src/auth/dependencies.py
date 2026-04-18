import logging

from auth.jwt import InvalidTokenError, JWTValidator
from auth.models import AuthenticatedUser
from fastapi import Depends, HTTPException, Request
from observability.metrics import auth_failures_total, authz_failures_total
from observability.security_events import log_auth_failure, log_authz_failure

logger = logging.getLogger("api-lab.auth")

_jwt_validator: JWTValidator | None = None


def set_jwt_validator(validator: JWTValidator):
    global _jwt_validator  # noqa: PLW0603
    _jwt_validator = validator


def _extract_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    return str(parts[1])


async def get_current_user(request: Request) -> AuthenticatedUser:
    if _jwt_validator is None:
        raise HTTPException(status_code=503, detail="Auth not initialized")

    token = _extract_token(request)
    try:
        return await _jwt_validator.validate(token)
    except InvalidTokenError as e:
        ip = request.client.host if request.client else "unknown"
        log_auth_failure(ip=ip, endpoint=str(request.url.path), reason=e.reason)
        auth_failures_total.labels(reason=e.reason).inc()
        raise HTTPException(status_code=401, detail=f"Invalid token: {e.reason}") from e


def require_roles(*required_roles: str):
    async def _check(user: AuthenticatedUser = Depends(get_current_user)):
        for role in required_roles:
            if role in user.roles:
                return user
        log_authz_failure(
            user_id=str(user.sub),
            endpoint="unknown",
            required_role=str(required_roles),
            actual_roles=user.roles,
        )
        authz_failures_total.labels(endpoint="unknown", role=str(required_roles)).inc()
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    return _check
