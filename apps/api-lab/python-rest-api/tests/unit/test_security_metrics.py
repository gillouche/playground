from observability.metrics import (
    auth_failures_total,
    authz_failures_total,
    login_attempts_total,
    rate_limit_rejections_total,
    registrations_total,
)


class TestSecurityMetricsExist:
    def test_auth_failures_total_has_reason_label(self):
        auth_failures_total.labels(reason="expired").inc(0)

    def test_authz_failures_total_has_endpoint_and_role_labels(self):
        authz_failures_total.labels(endpoint="/test", role="admin").inc(0)

    def test_rate_limit_rejections_total_has_endpoint_and_tier_labels(self):
        rate_limit_rejections_total.labels(endpoint="/test", tier="read").inc(0)

    def test_login_attempts_total_has_status_label(self):
        login_attempts_total.labels(status="success").inc(0)
        login_attempts_total.labels(status="failure").inc(0)

    def test_registrations_total_exists(self):
        registrations_total.inc(0)
