import json
import logging
import os
import sys
from datetime import UTC, datetime

from loguru import logger


def _get_otel_context() -> dict:
    """Extract OpenTelemetry trace_id and span_id from current context."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.trace_id:
            return {
                "trace_id": format(ctx.trace_id, "032x"),
                "span_id": format(ctx.span_id, "016x"),
            }
    except (ImportError, AttributeError):
        return {"trace_id": None, "span_id": None}
    return {"trace_id": None, "span_id": None}


def _json_sink(message):
    """Serialize log records as JSON with OTel context."""
    record = message.record
    otel = _get_otel_context()
    log_entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": record["level"].name,
        "logger": record["name"],
        "message": record["message"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
        "trace_id": otel["trace_id"],
        "span_id": otel["span_id"],
    }
    if record["exception"] is not None:
        log_entry["exception"] = str(record["exception"])
    if record["extra"]:
        log_entry["extra"] = {k: v for k, v in record["extra"].items() if k not in ("_sink",)}
    sys.stdout.write(json.dumps(log_entry, default=str) + "\n")
    sys.stdout.flush()


class _LoguruHandler(logging.Handler):
    """Bridge stdlib logging to loguru so third-party libs also produce JSON."""

    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(level: str = "INFO"):
    """Configure loguru as the sole logging backend with JSON output and OTel correlation."""
    level = os.environ.get("LOG_LEVEL", level).upper()

    # Remove default loguru handler
    logger.remove()
    # Add JSON sink
    logger.add(_json_sink, level=level, serialize=False)

    # Bridge stdlib logging to loguru
    logging.basicConfig(handlers=[_LoguruHandler()], level=0, force=True)

    # Quieten noisy libraries
    for name in ("uvicorn.access", "uvicorn.error", "asyncio"):
        logging.getLogger(name).setLevel(logging.WARNING)
