from typing import Any

from opentelemetry import trace
from opentelemetry.trace import StatusCode
from strawberry.extensions import SchemaExtension

_tracer = trace.get_tracer("api-lab.graphql")


class OpenTelemetryExtension(SchemaExtension):
    def on_operation(self):
        operation_name = self.execution_context.operation_name or "anonymous"
        operation_type = "query"
        if self.execution_context.query and "mutation" in self.execution_context.query.lower()[:20]:
            operation_type = "mutation"

        with _tracer.start_as_current_span(f"GraphQL.{operation_type}: {operation_name}") as span:
            span.set_attribute("graphql.operation.name", operation_name)
            span.set_attribute("graphql.operation.type", operation_type)
            try:
                yield
            except Exception as exc:
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
                raise

    def resolve(self, _next, root, info, *args: Any, **kwargs: Any):
        if info.field_name.startswith("_"):
            return _next(root, info, *args, **kwargs)

        with _tracer.start_as_current_span(f"GraphQL.resolve: {info.field_name}") as span:
            span.set_attribute("graphql.field.name", info.field_name)
            span.set_attribute(
                "graphql.parent.type", info.parent_type.name if info.parent_type else "unknown"
            )
            try:
                return _next(root, info, *args, **kwargs)
            except Exception as exc:
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
                raise
