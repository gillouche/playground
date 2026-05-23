import logging

import jwt as pyjwt
from fastapi import APIRouter, HTTPException, Request
from keycloak_client import KeycloakClient, KeycloakError
from observability.metrics import login_attempts_total, registrations_total
from observability.security_events import log_login_failure, log_login_success, log_registration
from pydantic import BaseModel, Field

logger = logging.getLogger("api-lab.auth")

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_keycloak_client: KeycloakClient | None = None


def set_keycloak_client(client: KeycloakClient):
    global _keycloak_client  # noqa: PLW0603
    _keycloak_client = client


def get_keycloak_client() -> KeycloakClient:
    if _keycloak_client is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return _keycloak_client


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class RegisterResponse(BaseModel):
    user_id: str
    username: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


@router.post("/register", status_code=201, response_model=RegisterResponse)
async def register(request: RegisterRequest, raw_request: Request):
    client = get_keycloak_client()
    try:
        user_id = await client.create_user(request.username, request.email, request.password)
    except KeycloakError as e:
        if e.status_code == 409:
            raise HTTPException(status_code=409, detail=e.detail) from e
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e

    ip = raw_request.client.host if raw_request.client else "unknown"
    log_registration(user_id=user_id, ip=ip)
    registrations_total.inc()
    return RegisterResponse(user_id=user_id, username=request.username)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, raw_request: Request):
    client = get_keycloak_client()
    ip = raw_request.client.host if raw_request.client else "unknown"
    try:
        tokens = await client.login(request.username, request.password)
    except KeycloakError as e:
        if e.status_code == 401:
            log_login_failure(username=request.username, ip=ip, reason="invalid_credentials")
            login_attempts_total.labels(status="failure").inc()
            raise HTTPException(status_code=401, detail="Invalid username or password") from e
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e

    try:
        unverified = pyjwt.decode(tokens["access_token"], options={"verify_signature": False})
        user_sub = unverified.get("sub", "unknown")
    except pyjwt.DecodeError as e:
        logger.warning("Failed to decode access_token for audit logging: %s", e)
        user_sub = "unknown"
    log_login_success(user_id=user_sub, ip=ip)
    login_attempts_total.labels(status="success").inc()
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest):
    client = get_keycloak_client()
    try:
        tokens = await client.refresh(request.refresh_token)
    except KeycloakError as e:
        if e.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token") from e
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e

    return TokenResponse(**tokens)


@router.post("/logout", status_code=204)
async def logout(request: LogoutRequest):
    client = get_keycloak_client()
    try:
        await client.logout(request.refresh_token)
    except KeycloakError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
