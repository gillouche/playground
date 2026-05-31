import os
import unittest.mock

import strawberry
from strawberry.extensions import DisableIntrospection, QueryDepthLimiter


@strawberry.type
class _NestedType:
    value: str


@strawberry.type
class _DeepQuery:
    @strawberry.field
    def level1(self) -> "_DeepQuery":
        return _DeepQuery()

    @strawberry.field
    def leaf(self) -> str:
        return "leaf"


@strawberry.type
class _SimpleQuery:
    @strawberry.field
    def hello(self) -> str:
        return "world"

    @strawberry.field
    def items(self) -> list[str]:
        return ["a", "b"]


def _make_simple_schema(**kwargs):
    return strawberry.Schema(query=_SimpleQuery, **kwargs)


def _make_deep_schema(**kwargs):
    return strawberry.Schema(query=_DeepQuery, **kwargs)


class TestQueryDepthLimiter:
    def test_shallow_query_passes(self):
        schema = _make_simple_schema(extensions=[QueryDepthLimiter(max_depth=10)])
        result = schema.execute_sync("{ hello }")
        assert result.errors is None

    def test_query_at_exact_depth_limit_passes(self):
        schema = _make_deep_schema(extensions=[QueryDepthLimiter(max_depth=2)])
        result = schema.execute_sync("{ level1 { level1 { leaf } } }")
        assert result.errors is None

    def test_query_exceeding_depth_limit_fails(self):
        schema = _make_deep_schema(extensions=[QueryDepthLimiter(max_depth=1)])
        result = schema.execute_sync("{ level1 { level1 { leaf } } }")
        assert result.errors is not None
        assert any("depth" in str(e).lower() for e in result.errors)

    def test_depth_limit_of_10_allows_reasonable_queries(self):
        schema = _make_deep_schema(extensions=[QueryDepthLimiter(max_depth=10)])
        result = schema.execute_sync("{ level1 { level1 { level1 { leaf } } } }")
        assert result.errors is None


class TestQueryComplexityLimiter:
    def _make_schema_with_complexity(self, max_complexity: int):
        from schema import (
            _MAX_QUERY_DEPTH,
            AddValidationRules,
            QueryDepthLimiter,
            _create_complexity_validator,
        )

        return strawberry.Schema(
            query=_SimpleQuery,
            extensions=[
                QueryDepthLimiter(max_depth=_MAX_QUERY_DEPTH),
                AddValidationRules([_create_complexity_validator(max_complexity)]),
            ],
        )

    def test_simple_query_within_complexity(self):
        schema = self._make_schema_with_complexity(1000)
        result = schema.execute_sync("{ hello }")
        assert result.errors is None

    def test_query_exceeding_complexity_fails(self):
        schema = self._make_schema_with_complexity(1)
        result = schema.execute_sync("{ hello items }")
        assert result.errors is not None
        assert any("complexity" in str(e).lower() for e in result.errors)

    def test_list_field_costs_more_than_scalar(self):
        from schema import _create_complexity_validator
        from strawberry.extensions import AddValidationRules

        schema_tight = strawberry.Schema(
            query=_SimpleQuery,
            extensions=[AddValidationRules([_create_complexity_validator(5)])],
        )
        result_scalar = schema_tight.execute_sync("{ hello }")
        assert result_scalar.errors is None

        schema_list = strawberry.Schema(
            query=_SimpleQuery,
            extensions=[AddValidationRules([_create_complexity_validator(5)])],
        )
        result_list = schema_list.execute_sync("{ items }")
        assert result_list.errors is not None

    def test_introspection_fields_excluded_from_complexity(self):
        from schema import _create_complexity_validator
        from strawberry.extensions import AddValidationRules

        schema = strawberry.Schema(
            query=_SimpleQuery,
            extensions=[AddValidationRules([_create_complexity_validator(1)])],
        )
        result = schema.execute_sync("{ __typename }")
        assert result.errors is None


class TestDisableIntrospection:
    def test_introspection_allowed_in_non_prod(self):
        schema = _make_simple_schema()
        result = schema.execute_sync("{ __typename }")
        assert result.errors is None
        assert result.data == {"__typename": "Simplequery"}

    def test_introspection_disabled_in_prod(self):
        schema = _make_simple_schema(extensions=[DisableIntrospection()])
        result = schema.execute_sync("{ __schema { types { name } } }")
        assert result.errors is not None

    def test_normal_queries_still_work_with_introspection_disabled(self):
        schema = _make_simple_schema(extensions=[DisableIntrospection()])
        result = schema.execute_sync("{ hello }")
        assert result.errors is None
        assert result.data == {"hello": "world"}


class TestBuildExtensions:
    def test_prod_environment_includes_disable_introspection(self):
        with unittest.mock.patch.dict(os.environ, {"ENVIRONMENT": "prod"}):
            from importlib import reload

            import schema as schema_module

            reload(schema_module)
            extensions = schema_module._build_extensions()
            assert any(isinstance(e, DisableIntrospection) for e in extensions)

    def test_dev_environment_excludes_disable_introspection(self):
        with unittest.mock.patch.dict(os.environ, {"ENVIRONMENT": "dev"}):
            from importlib import reload

            import schema as schema_module

            reload(schema_module)
            extensions = schema_module._build_extensions()
            assert not any(isinstance(e, DisableIntrospection) for e in extensions)

    def test_extensions_always_include_depth_limiter(self):
        from schema import _build_extensions

        extensions = _build_extensions()
        assert any(isinstance(e, QueryDepthLimiter) for e in extensions)

    def test_extensions_always_include_complexity_validator(self):
        from schema import AddValidationRules, _build_extensions

        extensions = _build_extensions()
        assert any(isinstance(e, AddValidationRules) for e in extensions)
