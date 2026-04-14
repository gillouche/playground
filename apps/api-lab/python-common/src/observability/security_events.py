import logging

logger = logging.getLogger("api-lab.security")


def log_auth_failure(ip: str, endpoint: str, reason: str, **kwargs):
    logger.warning(
        "Authentication failure",
        extra={
            "event_type": "security",
            "event": "auth.failure",
            "ip": ip,
            "endpoint": endpoint,
            "reason": reason,
            **kwargs,
        },
    )


def log_authz_failure(
    user_id: str, endpoint: str, required_role: str, actual_roles: list[str], **kwargs
):
    logger.warning(
        "Authorization failure",
        extra={
            "event_type": "security",
            "event": "authz.failure",
            "user_id": user_id,
            "endpoint": endpoint,
            "required_role": required_role,
            "actual_roles": actual_roles,
            **kwargs,
        },
    )


def log_rate_limit(ip: str, user_id: str | None, endpoint: str, tier: str, count: int, **kwargs):
    logger.warning(
        "Rate limit exceeded",
        extra={
            "event_type": "security",
            "event": "rate_limit.exceeded",
            "ip": ip,
            "user_id": user_id,
            "endpoint": endpoint,
            "tier": tier,
            "count": count,
            **kwargs,
        },
    )


def log_login_success(user_id: str, ip: str, **kwargs):
    logger.info(
        "Login success",
        extra={
            "event_type": "security",
            "event": "auth.login.success",
            "user_id": user_id,
            "ip": ip,
            **kwargs,
        },
    )


def log_login_failure(username: str, ip: str, reason: str, **kwargs):
    logger.warning(
        "Login failure",
        extra={
            "event_type": "security",
            "event": "auth.login.failure",
            "username": username,
            "ip": ip,
            "reason": reason,
            **kwargs,
        },
    )


def log_registration(user_id: str, ip: str, **kwargs):
    logger.info(
        "User registered",
        extra={
            "event_type": "security",
            "event": "auth.register",
            "user_id": user_id,
            "ip": ip,
            **kwargs,
        },
    )
