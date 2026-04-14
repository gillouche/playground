from unittest.mock import MagicMock, patch

import pytest
from opentelemetry.trace import StatusCode


class TestOpenTelemetryExtensionOnOperation:
    def test_yields_on_success(self):
        from tracing_extension import OpenTelemetryExtension

        ext = OpenTelemetryExtension.__new__(OpenTelemetryExtension)
        ext.execution_context = MagicMock()
        ext.execution_context.operation_name = "TestQuery"
        ext.execution_context.query = "query TestQuery { books { id } }"

        gen = ext.on_operation()
        next(gen)
        with pytest.raises(StopIteration):
            next(gen)

    def test_records_exception_on_error(self):
        from tracing_extension import OpenTelemetryExtension

        ext = OpenTelemetryExtension.__new__(OpenTelemetryExtension)
        ext.execution_context = MagicMock()
        ext.execution_context.operation_name = "FailingQuery"
        ext.execution_context.query = "query FailingQuery { books { id } }"

        mock_span = MagicMock()
        with patch("tracing_extension._tracer") as mock_tracer:
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(
                return_value=mock_span
            )
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)

            gen = ext.on_operation()
            next(gen)
            error = RuntimeError("something broke")
            with pytest.raises(RuntimeError, match="something broke"):
                gen.throw(RuntimeError, error)

            mock_span.set_status.assert_called_once_with(StatusCode.ERROR, "something broke")
            mock_span.record_exception.assert_called_once_with(error)


class TestOpenTelemetryExtensionResolve:
    def test_returns_result_on_success(self):
        from tracing_extension import OpenTelemetryExtension

        ext = OpenTelemetryExtension.__new__(OpenTelemetryExtension)
        info = MagicMock()
        info.field_name = "books"
        info.parent_type.name = "Query"

        def mock_next(_root, _info, *_args, **_kwargs):
            return "resolved_value"

        result = ext.resolve(mock_next, None, info)
        assert result == "resolved_value"

    def test_skips_internal_fields(self):
        from tracing_extension import OpenTelemetryExtension

        ext = OpenTelemetryExtension.__new__(OpenTelemetryExtension)
        info = MagicMock()
        info.field_name = "__typename"

        def mock_next(_root, _info, *_args, **_kwargs):
            return "Query"

        result = ext.resolve(mock_next, None, info)
        assert result == "Query"

    def test_records_exception_on_resolve_error(self):
        from tracing_extension import OpenTelemetryExtension

        ext = OpenTelemetryExtension.__new__(OpenTelemetryExtension)
        info = MagicMock()
        info.field_name = "books"
        info.parent_type.name = "Query"

        error = ValueError("resolve failed")

        def mock_next(_root, _info, *_args, **_kwargs):
            raise error

        mock_span = MagicMock()
        with patch("tracing_extension._tracer") as mock_tracer:
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(
                return_value=mock_span
            )
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)

            with pytest.raises(ValueError, match="resolve failed"):
                ext.resolve(mock_next, None, info)

            mock_span.set_status.assert_called_once_with(StatusCode.ERROR, "resolve failed")
            mock_span.record_exception.assert_called_once_with(error)
