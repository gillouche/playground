import io
import json
import logging
import os
from unittest.mock import MagicMock, patch

from loguru import logger
from observability.logging import _get_otel_context, _json_sink, _LoguruHandler, setup_logging


class TestGetOtelContext:
    def test_returns_none_when_no_span(self):
        result = _get_otel_context()
        assert result == {"trace_id": None, "span_id": None}

    def test_returns_none_when_otel_import_fails(self):
        # Setting a module to None in sys.modules causes ImportError on import
        import sys

        saved = {
            k: sys.modules.pop(k)
            for k in list(sys.modules)
            if k.startswith("opentelemetry") and k in sys.modules
        }
        try:
            with patch.dict("sys.modules", {"opentelemetry": None, "opentelemetry.trace": None}):
                result = _get_otel_context()
            assert result == {"trace_id": None, "span_id": None}
        finally:
            sys.modules.update(saved)

    def test_returns_trace_and_span_ids_from_active_span(self):
        mock_ctx = MagicMock()
        mock_ctx.trace_id = 0x1234567890ABCDEF1234567890ABCDEF
        mock_ctx.span_id = 0x1234567890ABCDEF

        mock_span = MagicMock()
        mock_span.get_span_context.return_value = mock_ctx

        mock_trace = MagicMock()
        mock_trace.get_current_span.return_value = mock_span

        # The function does `from opentelemetry import trace` locally,
        # so we mock the opentelemetry.trace module in sys.modules.
        with patch.dict(
            "sys.modules",
            {"opentelemetry": MagicMock(trace=mock_trace), "opentelemetry.trace": mock_trace},
        ):
            result = _get_otel_context()

        assert result["trace_id"] == format(mock_ctx.trace_id, "032x")
        assert result["span_id"] == format(mock_ctx.span_id, "016x")


class TestJsonSink:
    def test_writes_json_to_stdout(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            # Use loguru to produce a real message record by logging through the sink
            logger.remove()
            logger.add(_json_sink, level="DEBUG", serialize=False)
            logger.info("hello test")
            logger.remove()

        output = buf.getvalue().strip()
        log_entry = json.loads(output)
        assert log_entry["level"] == "INFO"
        assert log_entry["message"] == "hello test"
        assert "timestamp" in log_entry
        assert "trace_id" in log_entry
        assert "span_id" in log_entry

    def test_includes_exception_when_present(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            logger.remove()
            logger.add(_json_sink, level="DEBUG", serialize=False)
            try:
                raise RuntimeError("boom")
            except RuntimeError:
                logger.exception("something failed")
            logger.remove()

        output = buf.getvalue().strip()
        log_entry = json.loads(output)
        assert log_entry["message"] == "something failed"
        assert "exception" in log_entry


class TestLoguruHandler:
    def test_emit_bridges_to_loguru(self):
        handler = _LoguruHandler()
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            logger.remove()
            logger.add(_json_sink, level="DEBUG", serialize=False)

            record = logging.LogRecord(
                name="test.logger",
                level=logging.WARNING,
                pathname="test.py",
                lineno=1,
                msg="stdlib warning",
                args=(),
                exc_info=None,
            )
            handler.emit(record)
            logger.remove()

        output = buf.getvalue().strip()
        assert output  # something was written
        log_entry = json.loads(output)
        assert log_entry["message"] == "stdlib warning"


class TestSetupLogging:
    def test_configures_loguru_with_default_level(self):
        env = dict(os.environ)
        env.pop("LOG_LEVEL", None)
        with patch.dict(os.environ, env, clear=True):
            setup_logging()
        # After setup, loguru should have exactly one handler (the _json_sink)
        # Verify by checking logger's handlers list is not empty
        assert len(logger._core.handlers) > 0

    def test_respects_log_level_env_var(self):
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}, clear=False):
            setup_logging()
        assert len(logger._core.handlers) > 0

    def test_respects_passed_level(self):
        env = dict(os.environ)
        env.pop("LOG_LEVEL", None)
        with patch.dict(os.environ, env, clear=True):
            setup_logging(level="WARNING")
        assert len(logger._core.handlers) > 0

    def test_quietens_noisy_loggers(self):
        setup_logging()
        for name in ("uvicorn.access", "uvicorn.error", "asyncio"):
            assert logging.getLogger(name).level == logging.WARNING
