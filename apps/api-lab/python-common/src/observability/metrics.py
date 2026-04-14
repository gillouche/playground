from prometheus_client import Counter, Gauge, Histogram

books_created_total = Counter("api_lab_books_created_total", "Total books created")
reservations_created_total = Counter(
    "api_lab_reservations_created_total", "Total reservations created"
)
reservations_returned_total = Counter(
    "api_lab_reservations_returned_total", "Total reservations returned"
)
cache_hits_total = Counter("api_lab_cache_hits_total", "Cache hits", ["operation"])
cache_misses_total = Counter("api_lab_cache_misses_total", "Cache misses", ["operation"])
db_query_duration_seconds = Histogram(
    "api_lab_db_query_duration_seconds", "DB query duration", ["operation"]
)
cache_op_duration_seconds = Histogram(
    "api_lab_cache_op_duration_seconds", "Cache operation duration", ["operation"]
)
books_available_gauge = Gauge("api_lab_books_available", "Available books count")
active_reservations_gauge = Gauge("api_lab_active_reservations", "Active reservations count")

auth_failures_total = Counter("api_lab_auth_failures_total", "Authentication failures", ["reason"])
authz_failures_total = Counter(
    "api_lab_authz_failures_total", "Authorization failures", ["endpoint", "role"]
)
rate_limit_rejections_total = Counter(
    "api_lab_rate_limit_rejections_total", "Rate limit rejections", ["endpoint", "tier"]
)
login_attempts_total = Counter("api_lab_login_attempts_total", "Login attempts", ["status"])
registrations_total = Counter("api_lab_registrations_total", "User registrations")


def setup_metrics(app):
    """Setup FastAPI metrics instrumentation. Requires prometheus-fastapi-instrumentator."""
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator().instrument(app).expose(app)
