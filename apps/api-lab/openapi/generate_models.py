#!/usr/bin/env python3
"""Generate Python models and API interface from OpenAPI 3.1 spec.

This script is run by Bazel at build time to ensure generated code
always matches the OpenAPI specification.

Usage:
    python generate_models.py --spec openapi.yaml --out-dir output/generated
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import yaml

# Mapping from OpenAPI types/formats to Python type annotations
_TYPE_MAP = {
    ("string", None): "str",
    ("string", "uuid"): "uuid.UUID",
    ("string", "date-time"): "datetime",
    ("integer", None): "int",
    ("boolean", None): "bool",
    ("number", None): "float",
}


def _resolve_ref(spec: dict, ref: str) -> tuple[str, dict]:
    """Resolve a $ref to its schema name and definition."""
    # e.g. "#/components/schemas/BookResponse" -> "BookResponse"
    parts = ref.lstrip("#/").split("/")
    obj = spec
    for part in parts:
        obj = obj[part]
    return parts[-1], obj


def _python_type(prop: dict, spec: dict, nullable: bool = False) -> str:
    """Convert an OpenAPI property schema to a Python type string."""
    if "$ref" in prop:
        name, _ = _resolve_ref(spec, prop["$ref"])
        return name

    # Handle nullable union types: type: [string, "null"]
    if isinstance(prop.get("type"), list):
        types = [t for t in prop["type"] if t != "null"]
        is_nullable = "null" in prop["type"]
        if types:
            inner = _python_type(
                {"type": types[0], **{k: v for k, v in prop.items() if k != "type"}}, spec
            )
            return f"{inner} | None" if is_nullable else inner

    schema_type = prop.get("type", "str")
    fmt = prop.get("format")

    if schema_type == "array":
        items = prop.get("items", {})
        item_type = _python_type(items, spec)
        base = f"list[{item_type}]"
    else:
        base = _TYPE_MAP.get((schema_type, fmt), _TYPE_MAP.get((schema_type, None), "str"))

    if nullable:
        return f"{base} | None"
    return base


def _is_enum(schema: dict) -> bool:
    return "enum" in schema


def _has_constraints(prop: dict) -> bool:
    constraint_keys = {
        "minLength",
        "maxLength",
        "pattern",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "minItems",
        "maxItems",
    }
    return bool(constraint_keys & prop.keys())


def _has_literal_enum(prop: dict) -> bool:
    return "enum" in prop and prop.get("type") == "string"


def _needs_field_import(schemas: dict) -> bool:
    for _name, schema in schemas.items():
        for _pname, prop in schema.get("properties", {}).items():
            if _has_constraints(prop):
                return True
    return False


def _needs_literal_import(schemas: dict) -> bool:
    for _name, schema in schemas.items():
        for _pname, prop in schema.get("properties", {}).items():
            if _has_literal_enum(prop):
                return True
    return False


_CONSTRAINT_MAP = {
    "minLength": "min_length",
    "maxLength": "max_length",
    "pattern": "pattern",
    "minimum": "ge",
    "maximum": "le",
    "exclusiveMinimum": "gt",
    "exclusiveMaximum": "lt",
    "minItems": "min_length",
    "maxItems": "max_length",
}


def _build_field_kwargs(prop: dict) -> dict[str, object]:
    kwargs: dict[str, object] = {}
    for oa_key, pydantic_key in _CONSTRAINT_MAP.items():
        if oa_key in prop:
            val = prop[oa_key]
            if oa_key == "pattern":
                val = f'r"{val}"'
            kwargs[pydantic_key] = val
    return kwargs


def _format_field_call(kwargs: dict[str, object], default: object = ...) -> str:
    parts = []
    if default is not ...:
        if default is None:
            parts.append("default=None")
        elif isinstance(default, str | bool):
            parts.append(f"default={default!r}")
        else:
            parts.append(f"default={default}")
    for key, val in kwargs.items():
        parts.append(f"{key}={val}")
    return f"Field({', '.join(parts)})"


def _generate_models(spec: dict) -> str:  # noqa: PLR0912
    """Generate Pydantic model classes from OpenAPI schemas."""
    schemas = spec.get("components", {}).get("schemas", {})

    needs_field = _needs_field_import(schemas)
    needs_literal = _needs_literal_import(schemas)

    pydantic_imports = ["BaseModel"]
    if needs_field:
        pydantic_imports.append("Field")

    typing_imports = []
    if needs_literal:
        typing_imports.append("Literal")

    lines = [
        "# Generated from openapi.yaml - DO NOT EDIT MANUALLY",
        "# Run: ./apps/api-lab/openapi/generate.sh python",
        "",
        "import uuid",
        "from datetime import datetime",
        "from enum import Enum",
    ]

    if typing_imports:
        lines.append(f"from typing import {', '.join(typing_imports)}")

    lines.append("")
    lines.append(f"from pydantic import {', '.join(pydantic_imports)}")
    lines.append("")
    lines.append("")

    enums: list[tuple[str, dict]] = []
    bases: list[tuple[str, dict]] = []
    derived: list[tuple[str, dict]] = []

    for name, schema in schemas.items():
        if _is_enum_schema(schema, schemas):
            enums.append((name, schema))
        elif "allOf" in schema:
            derived.append((name, schema))
        else:
            bases.append((name, schema))

    enum_types = _find_enum_types(schemas)
    for name, schema in enums:
        if name not in enum_types and "enum" in schema:
            enum_types[name] = schema["enum"]
    lines.extend(_generate_enum_lines(enum_types))

    all_models = []

    for name, schema in bases:
        if name in enum_types:
            continue
        all_models.append(_generate_model_class(name, schema, spec, None, enum_types))

    for name, schema in derived:
        parent_name = None
        extra_props = {}
        for item in schema.get("allOf", []):
            if "$ref" in item:
                ref_name, _ = _resolve_ref(spec, item["$ref"])
                parent_name = ref_name
            elif "properties" in item:
                extra_props = item.get("properties", {})

        all_models.append(
            _generate_model_class(name, {"properties": extra_props}, spec, parent_name, enum_types)
        )

    for i, model_lines in enumerate(all_models):
        if i > 0:
            lines.append("")
        lines.extend(model_lines)
        lines.append("")

    return "\n".join(lines)


def _generate_enum_lines(enum_types: dict[str, list[str]]) -> list[str]:
    """Generate enum class definitions."""
    if not enum_types:
        return []
    lines: list[str] = []
    for enum_name, enum_values in enum_types.items():
        lines.append(f"class {enum_name}(str, Enum):")
        for val in enum_values:
            lines.append(f'    {val} = "{val}"')
        lines.append("")
        lines.append("")
    return lines


def _is_enum_schema(schema: dict, _schemas: dict) -> bool:
    """Check if a schema is purely an enum reference."""
    return "enum" in schema


def _find_enum_types(schemas: dict) -> dict[str, list[str]]:
    """Find all enum types defined in schema properties."""
    enums: dict[str, list[str]] = {}
    for _name, schema in schemas.items():
        for _prop_name, prop in schema.get("properties", {}).items():
            if "enum" in prop:
                if _has_literal_enum(prop):
                    continue
                enum_name = _derive_enum_name(_name, _prop_name)
                enums[enum_name] = prop["enum"]
    return enums


def _derive_enum_name(schema_name: str, prop_name: str) -> str:
    """Derive an enum class name from schema + property name."""
    # e.g. Reservation.status -> ReservationStatus
    return f"{schema_name}{prop_name.title().replace('_', '')}"


@dataclass
class _ModelGenContext:
    spec: dict
    enum_types: dict | None
    model_name: str


def _generate_property_line(  # noqa: PLR0912
    prop_name: str, prop_schema: dict, is_required: bool, ctx: _ModelGenContext
) -> str:
    """Generate a single property line for a Pydantic model class."""
    is_nullable = isinstance(prop_schema.get("type"), list) and "null" in prop_schema["type"]
    constraints = _build_field_kwargs(prop_schema)
    has_literal = _has_literal_enum(prop_schema)

    if has_literal:
        enum_vals = prop_schema["enum"]
        literal_args = ", ".join(f'"{v}"' for v in enum_vals)
        py_type = f"Literal[{literal_args}]"
    elif ctx.enum_types and "enum" in prop_schema:
        enum_name = _derive_enum_name(ctx.model_name, prop_name)
        if enum_name in ctx.enum_types:
            py_type = enum_name
            if is_nullable:
                py_type = f"{py_type} | None"
        else:
            py_type = _python_type(prop_schema, ctx.spec, nullable=is_nullable)
    else:
        py_type = _python_type(prop_schema, ctx.spec, nullable=is_nullable)

    default_val = prop_schema.get("default")

    if has_literal and default_val is not None:
        return f'    {prop_name}: {py_type} = "{default_val}"'

    if constraints:
        if default_val is not None:
            field_str = _format_field_call(constraints, default=default_val)
        elif not is_required and not is_nullable:
            py_type = f"{py_type} | None"
            field_str = _format_field_call(constraints, default=None)
        elif is_nullable and not is_required:
            field_str = _format_field_call(constraints, default=None)
        else:
            field_str = _format_field_call(constraints)
        return f"    {prop_name}: {py_type} = {field_str}"

    if default_val is not None:
        return f"    {prop_name}: {py_type} = {default_val!r}"
    if not is_required and not is_nullable:
        py_type = f"{py_type} | None"
        return f"    {prop_name}: {py_type} = None"
    if is_nullable and not is_required:
        return f"    {prop_name}: {py_type} = None"
    return f"    {prop_name}: {py_type}"


def _generate_model_class(
    name: str, schema: dict, spec: dict, parent: str | None, enum_types: dict | None = None
) -> list[str]:
    """Generate a single Pydantic model class."""
    props = schema.get("properties", {})
    required = set(schema.get("required", []))

    base = parent if parent else "BaseModel"
    lines = [f"class {name}({base}):"]

    if not props and parent:
        lines.append('    model_config = {"from_attributes": True}')
        return lines

    if not props:
        lines.append("    pass")
        return lines

    ctx = _ModelGenContext(spec=spec, enum_types=enum_types, model_name=name)
    for prop_name, prop_schema in props.items():
        is_required = prop_name in required
        lines.append(_generate_property_line(prop_name, prop_schema, is_required, ctx))

    orm_models = {"Book", "Reservation"}
    if parent or name in orm_models:
        lines.append("")
        lines.append('    model_config = {"from_attributes": True}')

    return lines


def _generate_interface(spec: dict) -> str:
    """Generate an abstract API interface from OpenAPI paths."""
    paths = spec.get("paths", {})

    lines = [
        "# Generated from openapi.yaml — DO NOT EDIT MANUALLY",
        "# Regenerated automatically by Bazel at build time.",
        "",
        "from __future__ import annotations",
        "",
        "import abc",
        "from typing import TYPE_CHECKING",
        "",
        "if TYPE_CHECKING:",
        "    import uuid",
        "",
        "    from generated.models import (",
    ]

    # Collect all referenced schemas
    schema_names = set()
    for _path, methods in paths.items():
        for _method, op in methods.items():
            if not isinstance(op, dict):
                continue
            # Collect from responses
            for _code, resp in op.get("responses", {}).items():
                content = resp.get("content", {})
                for _mime, media in content.items():
                    schema = media.get("schema", {})
                    _collect_schema_refs(schema, schema_names)
            # Collect from requestBody
            rb = op.get("requestBody", {})
            for _mime, media in rb.get("content", {}).items():
                schema = media.get("schema", {})
                _collect_schema_refs(schema, schema_names)

    for name in sorted(schema_names):
        lines.append(f"        {name},")

    lines.extend(
        [
            "    )",
            "",
            "",
            "class LibraryAPI(abc.ABC):",
            '    """Abstract interface for the Library Book Management API.',
            "",
            "    Each method corresponds to an operationId in the OpenAPI spec.",
            "    Implement this class and wire the methods to your framework of choice",
            "    (FastAPI, Flask, etc.).",
            '    """',
            "",
        ]
    )

    # Group by tag/section
    current_section = None
    for path, methods in paths.items():
        for method, op in methods.items():
            if not isinstance(op, dict) or "operationId" not in op:
                continue

            op_id = op["operationId"]
            section = _derive_section(path)
            if section != current_section:
                lines.append(f"    # ----- {section} " + "-" * (55 - len(section)))
                lines.append("")
                current_section = section

            # Build method signature
            params = _build_params(op, spec)
            return_type = _build_return_type(op, spec)
            method_name = _camel_to_snake(op_id)

            sig_parts = ["self"]
            if params:
                sig_parts.append("*")
                sig_parts.extend(params)

            sig = ", ".join(sig_parts)
            lines.append("    @abc.abstractmethod")
            lines.append(f"    async def {method_name}({sig}) -> {return_type}:")
            lines.append(f'        """{method.upper()} {path}  (operationId: {op_id})"""')
            lines.append("        ...")
            lines.append("")

    return "\n".join(lines)


def _collect_schema_refs(schema: dict, refs: set[str]) -> None:
    """Recursively collect $ref schema names."""
    if "$ref" in schema:
        name = schema["$ref"].split("/")[-1]
        refs.add(name)
    if "items" in schema:
        _collect_schema_refs(schema["items"], refs)
    for item in schema.get("allOf", []):
        _collect_schema_refs(item, refs)


def _derive_section(path: str) -> str:
    """Derive a section name from the API path."""
    if "books" in path:
        return "Books"
    if "inventory" in path:
        return "Inventory"
    if "reservations" in path:
        return "Reservations"
    if "health" in path or "ready" in path:
        return "Health / Info"
    if "info" in path:
        return "Health / Info"
    return "Other"


def _resolve_param(param: dict, spec: dict) -> dict:
    """Resolve a parameter, following $ref if present."""
    if "$ref" in param:
        _, resolved = _resolve_ref(spec, param["$ref"])
        return resolved
    return param


def _build_params(op: dict, spec: dict) -> list[str]:
    """Build parameter list for a method."""
    params = []
    for raw_param in op.get("parameters", []):
        param = _resolve_param(raw_param, spec)
        if param.get("in") == "header":
            continue
        name = param["name"]
        schema = param.get("schema", {})
        py_type = _python_type(schema, spec)
        required = param.get("required", False)
        if not required:
            params.append(f"{name}: {py_type} | None = None")
        else:
            params.append(f"{name}: {py_type}")

    rb = op.get("requestBody", {})
    for _mime, media in rb.get("content", {}).items():
        schema = media.get("schema", {})
        py_type = _python_type(schema, spec)
        params.append(f"body: {py_type}")

    return params


def _build_return_type(op: dict, spec: dict) -> str:
    """Build return type from the success response."""
    for code, resp in op.get("responses", {}).items():
        if code.startswith("2"):
            content = resp.get("content", {})
            for _mime, media in content.items():
                schema = media.get("schema", {})
                return _python_type(schema, spec)
            if code == "204":
                return "None"
    return "None"


def _camel_to_snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    result = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0:
            result.append("_")
        result.append(ch.lower())
    return "".join(result)


def main():
    parser = argparse.ArgumentParser(description="Generate Python code from OpenAPI spec")
    parser.add_argument("--spec", required=True, help="Path to openapi.yaml")
    parser.add_argument("--out-dir", required=True, help="Output directory for generated files")
    args = parser.parse_args()

    spec_path = Path(args.spec)
    out_dir = Path(args.out_dir)

    spec = yaml.safe_load(spec_path.read_text())
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "models.py").write_text(_generate_models(spec))
    (out_dir / "api_interface.py").write_text(_generate_interface(spec))
    (out_dir / "__init__.py").write_text("")


if __name__ == "__main__":
    main()
