#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

import yaml


def generate_openapi_docs(spec_path: Path, output_path: Path) -> bool:
    if not spec_path.exists():
        print(f"WARNING: OpenAPI spec not found at {spec_path}", file=sys.stderr)
        return False

    with open(spec_path) as f:
        spec = yaml.safe_load(f)

    lines = ["# REST API Reference\n"]
    lines.append(f"**{spec.get('info', {}).get('title', 'API')}**")
    lines.append(f"Version: {spec.get('info', {}).get('version', 'unknown')}\n")

    if "info" in spec and "description" in spec["info"]:
        lines.append(f"{spec['info']['description']}\n")

    paths = spec.get("paths", {})
    for path, methods in sorted(paths.items()):
        lines.append(f"## `{path}`\n")
        for method, details in methods.items():
            if method in ("get", "post", "put", "delete", "patch"):
                lines.append(f"### {method.upper()}")
                if "summary" in details:
                    lines.append(f"**{details['summary']}**\n")
                if "description" in details:
                    lines.append(f"{details['description']}\n")
                if "operationId" in details:
                    lines.append(f"Operation ID: `{details['operationId']}`\n")

                params = details.get("parameters", [])
                if params:
                    lines.append("**Parameters:**\n")
                    lines.append("| Name | In | Type | Required | Description |")
                    lines.append("|------|-----|------|----------|-------------|")
                    for p in params:
                        schema = p.get("schema", {})
                        ptype = schema.get("type", "string")
                        required = "Yes" if p.get("required", False) else "No"
                        desc = p.get("description", "")
                        lines.append(
                            f"| `{p['name']}` | {p.get('in', '')} "
                            f"| {ptype} | {required} | {desc} |"
                        )
                    lines.append("")

                req_body = details.get("requestBody", {})
                if req_body:
                    lines.append("**Request Body:**\n")
                    content = req_body.get("content", {})
                    for media_type, media_spec in content.items():
                        lines.append(f"Content-Type: `{media_type}`\n")
                        schema = media_spec.get("schema", {})
                        ref = schema.get("$ref", "")
                        if ref:
                            schema_name = ref.split("/")[-1]
                            lines.append(f"Schema: `{schema_name}`\n")

                responses = details.get("responses", {})
                if responses:
                    lines.append("**Responses:**\n")
                    lines.append("| Status | Description | Schema |")
                    lines.append("|--------|-------------|--------|")
                    for status, resp in sorted(responses.items()):
                        desc = resp.get("description", "")
                        schema_name = ""
                        content = resp.get("content", {})
                        for _media_type, media_spec in content.items():
                            ref = media_spec.get("schema", {}).get("$ref", "")
                            if ref:
                                schema_name = f"`{ref.split('/')[-1]}`"
                        lines.append(f"| {status} | {desc} | {schema_name} |")
                    lines.append("")

    schemas = spec.get("components", {}).get("schemas", {})
    if schemas:
        lines.append("## Schemas\n")
        for name, schema in sorted(schemas.items()):
            lines.append(f"### {name}\n")
            if "description" in schema:
                lines.append(f"{schema['description']}\n")
            if "enum" in schema:
                lines.append(f"**Enum values:** {', '.join(f'`{v}`' for v in schema['enum'])}\n")
            properties = schema.get("properties", {})
            required_fields = schema.get("required", [])
            if properties:
                lines.append("| Field | Type | Required | Description |")
                lines.append("|-------|------|----------|-------------|")
                for field_name, field_spec in properties.items():
                    ftype = field_spec.get("type", "")
                    ref = field_spec.get("$ref", "")
                    if ref:
                        ftype = ref.split("/")[-1]
                    if "items" in field_spec:
                        items_ref = field_spec["items"].get("$ref", "")
                        items_type = field_spec["items"].get("type", "")
                        ftype = f"array[{items_ref.split('/')[-1] if items_ref else items_type}]"
                    req = "Yes" if field_name in required_fields else "No"
                    desc = field_spec.get("description", "")
                    lines.append(f"| `{field_name}` | {ftype} | {req} | {desc} |")
                lines.append("")

    output_path.write_text("\n".join(lines))
    return True


def generate_proto_docs(proto_dir: Path, output_path: Path) -> bool:
    proto_files = list(proto_dir.rglob("*.proto"))
    if not proto_files:
        print(f"WARNING: No .proto files found in {proto_dir}", file=sys.stderr)
        return False

    lines = ["# gRPC API Reference\n"]

    for proto_file in sorted(proto_files):
        content = proto_file.read_text()
        current_comment = []
        in_table = False

        lines.append(f"Source: `{proto_file.relative_to(proto_dir.parent.parent)}`\n")

        for line in content.splitlines():
            stripped = line.strip()

            if stripped.startswith("//"):
                current_comment.append(stripped.lstrip("/ "))
                continue

            if stripped.startswith("service "):
                in_table = False
                service_name = stripped.split()[1].rstrip(" {")
                lines.append(f"## Service: {service_name}\n")
                if current_comment:
                    lines.append(" ".join(current_comment) + "\n")
                current_comment = []

            elif stripped.startswith("rpc "):
                parts = stripped.replace("(", " ").replace(")", " ").split()
                if len(parts) >= 5:
                    method = parts[1]
                    input_type = parts[2]
                    output_type = parts[4]
                    lines.append(f"### `{method}`\n")
                    if current_comment:
                        lines.append(" ".join(current_comment) + "\n")
                    lines.append(f"- **Input:** `{input_type}`")
                    lines.append(f"- **Output:** `{output_type}`\n")
                current_comment = []

            elif stripped.startswith("message "):
                in_table = False
                msg_name = stripped.split()[1].rstrip(" {")
                lines.append(f"## Message: {msg_name}\n")
                if current_comment:
                    lines.append(" ".join(current_comment) + "\n")
                current_comment = []

            elif "=" in stripped and not stripped.startswith("//") and not stripped.startswith(
                "syntax"
            ):
                field_parts = stripped.rstrip(";").split()
                if len(field_parts) >= 3 and field_parts[-1].isdigit():
                    field_type = field_parts[0]
                    field_name = field_parts[1]
                    field_num = field_parts[-1]
                    comment = " ".join(current_comment) if current_comment else ""
                    if not in_table:
                        lines.append("| Field | Type | Number | Description |")
                        lines.append("|-------|------|--------|-------------|")
                        in_table = True
                    lines.append(
                        f"| `{field_name}` | `{field_type}` | {field_num} | {comment} |"
                    )
                    current_comment = []

            elif stripped == "}" or stripped == "":
                if in_table:
                    in_table = False
                    lines.append("")
                current_comment = []

    output_path.write_text("\n".join(lines))
    return True


def generate_graphql_docs(schema_module_path: Path, output_path: Path) -> bool:
    if not schema_module_path.exists():
        print(
            f"WARNING: GraphQL schema not found at {schema_module_path}",
            file=sys.stderr,
        )
        return False

    gateway_dir = schema_module_path.parent.parent
    extract_script = (
        "import sys, types; sys.path.insert(0, 'src'); "
        "sys.modules['strawberry.fastapi'] = types.ModuleType('strawberry.fastapi'); "
        "sys.modules['strawberry.fastapi'].GraphQLRouter = None; "
        "from schema import graphql_schema; print(str(graphql_schema))"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", extract_script],
            capture_output=True,
            text=True,
            cwd=gateway_dir,
            timeout=30,
        )
        if result.returncode != 0:
            print(
                f"WARNING: Could not export GraphQL schema: {result.stderr.strip()}",
                file=sys.stderr,
            )
            return False
        sdl = result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"WARNING: Could not export GraphQL schema: {e}", file=sys.stderr)
        return False

    lines = ["# GraphQL API Reference\n"]
    lines.append("Auto-generated from Strawberry schema definition.\n")

    current_type = None
    fields_started = False

    for line in sdl.splitlines():
        stripped = line.strip()

        if stripped.startswith("type Query"):
            current_type = "Queries"
            lines.append(f"## {current_type}\n")
            fields_started = False
        elif stripped.startswith("type Mutation"):
            current_type = "Mutations"
            lines.append(f"## {current_type}\n")
            fields_started = False
        elif stripped.startswith("type ") and not stripped.startswith("type Query") and not stripped.startswith("type Mutation"):
            type_name = stripped.split()[1].rstrip(" {")
            current_type = type_name
            lines.append(f"## Type: {type_name}\n")
            fields_started = False
        elif stripped.startswith("enum "):
            enum_name = stripped.split()[1].rstrip(" {")
            lines.append(f"## Enum: {enum_name}\n")
            current_type = "enum"
            fields_started = False
        elif stripped == "}" and current_type:
            if fields_started:
                lines.append("")
            current_type = None
            fields_started = False
        elif current_type and stripped and not stripped.startswith("{"):
            if current_type == "enum":
                lines.append(f"- `{stripped}`")
            else:
                if not fields_started:
                    lines.append("| Field | Type |")
                    lines.append("|-------|------|")
                    fields_started = True
                parts = stripped.rstrip("!").split(":")
                if len(parts) >= 2:
                    field_name = parts[0].strip().split("(")[0]
                    field_type = parts[-1].strip().rstrip("!")
                    lines.append(f"| `{field_name}` | `{field_type}` |")

    output_path.write_text("\n".join(lines))
    return True


def main():
    repo_root = Path(__file__).parent.parent
    output_dir = Path(__file__).parent / "content" / "apps" / "api-lab" / "api-reference"
    output_dir.mkdir(parents=True, exist_ok=True)

    openapi_spec = repo_root / "apps" / "api-lab" / "openapi" / "openapi.yaml"
    proto_dir = repo_root / "apps" / "api-lab" / "openapi" / "proto"
    graphql_schema_path = repo_root / "apps" / "api-lab" / "graphql-gateway" / "src" / "schema.py"

    results = {
        "OpenAPI": generate_openapi_docs(openapi_spec, output_dir / "rest-api.md"),
        "Protobuf": generate_proto_docs(proto_dir, output_dir / "grpc-api.md"),
        "GraphQL": generate_graphql_docs(graphql_schema_path, output_dir / "graphql-api.md"),
    }

    for name, success in results.items():
        status = "OK" if success else "SKIPPED"
        print(f"  {name}: {status}")


if __name__ == "__main__":
    main()
