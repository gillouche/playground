import logging

from observability.security_events import (
    log_auth_failure,
    log_authz_failure,
    log_login_failure,
    log_login_success,
    log_rate_limit,
    log_registration,
)


class TestLogAuthFailure:
    def test_logs_warning_with_security_event_fields(self, caplog):
        with caplog.at_level(logging.WARNING, logger="api-lab.security"):
            log_auth_failure(ip="192.168.1.1", endpoint="/api/v1/books", reason="expired")

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "WARNING"
        assert record.event_type == "security"
        assert record.event == "auth.failure"
        assert record.ip == "192.168.1.1"
        assert record.endpoint == "/api/v1/books"
        assert record.reason == "expired"

    def test_passes_extra_kwargs(self, caplog):
        with caplog.at_level(logging.WARNING, logger="api-lab.security"):
            log_auth_failure(
                ip="10.0.0.1", endpoint="/test", reason="bad_sig", request_id="abc-123"
            )

        record = caplog.records[0]
        assert record.request_id == "abc-123"


class TestLogAuthzFailure:
    def test_logs_warning_with_authorization_fields(self, caplog):
        with caplog.at_level(logging.WARNING, logger="api-lab.security"):
            log_authz_failure(
                user_id="user-42",
                endpoint="/api/v1/admin",
                required_role="admin",
                actual_roles=["user"],
            )

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.event == "authz.failure"
        assert record.user_id == "user-42"
        assert record.required_role == "admin"
        assert record.actual_roles == ["user"]


class TestLogRateLimit:
    def test_logs_warning_with_rate_limit_fields(self, caplog):
        with caplog.at_level(logging.WARNING, logger="api-lab.security"):
            log_rate_limit(
                ip="203.0.113.50",
                user_id=None,
                endpoint="/api/v1/books",
                tier="read",
                count=201,
            )

        record = caplog.records[0]
        assert record.event == "rate_limit.exceeded"
        assert record.ip == "203.0.113.50"
        assert record.user_id is None
        assert record.tier == "read"
        assert record.count == 201


class TestLogLoginSuccess:
    def test_logs_info_with_login_success_fields(self, caplog):
        with caplog.at_level(logging.INFO, logger="api-lab.security"):
            log_login_success(user_id="user-99", ip="10.0.0.5")

        record = caplog.records[0]
        assert record.levelname == "INFO"
        assert record.event == "auth.login.success"
        assert record.user_id == "user-99"
        assert record.ip == "10.0.0.5"


class TestLogLoginFailure:
    def test_logs_warning_with_login_failure_fields(self, caplog):
        with caplog.at_level(logging.WARNING, logger="api-lab.security"):
            log_login_failure(username="baduser", ip="10.0.0.5", reason="invalid_credentials")

        record = caplog.records[0]
        assert record.event == "auth.login.failure"
        assert record.username == "baduser"
        assert record.reason == "invalid_credentials"


class TestLogRegistration:
    def test_logs_info_with_registration_fields(self, caplog):
        with caplog.at_level(logging.INFO, logger="api-lab.security"):
            log_registration(user_id="new-user-1", ip="10.0.0.1")

        record = caplog.records[0]
        assert record.event == "auth.register"
        assert record.user_id == "new-user-1"
