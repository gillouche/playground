# Documentation Site Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a comprehensive documentation website for the Playground monorepo using Zensical, with auto-generated API references and offline-rendered mermaid diagrams.

**Architecture:** Standalone `docs/` uv project decoupled from Bazel. A shell script orchestrates diagram rendering (mmdc), API spec extraction (custom Python script), and Zensical build/serve. Content organized by app with shared common sections.

**Tech Stack:** Zensical (static site generator), uv (Python project management), mermaid-cli/mmdc (diagram rendering via npx), PyYAML (spec parsing), Strawberry (GraphQL SDL export)

**Spec:** `docs/superpowers/specs/2026-03-12-documentation-site-design.md`

---

## Chunk 1: Project Scaffolding and Tooling

### Task 1: Initialize docs/ as a uv project

**Files:**
- Create: `docs/pyproject.toml`
- Create: `docs/.python-version`
- Create: `docs/.gitignore`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "playground-docs"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = [
    "zensical",
    "pyyaml",
    "strawberry-graphql",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 2: Create .python-version**

```
3.14
```

- [ ] **Step 3: Create .gitignore**

```gitignore
.venv/
__pycache__/
*.pyc
site/

content/assets/diagrams/*.svg
content/apps/api-lab/api-reference/rest-api.md
content/apps/api-lab/api-reference/grpc-api.md
content/apps/api-lab/api-reference/graphql-api.md
```

- [ ] **Step 4: Run uv sync to install dependencies and generate lockfile**

Run: `cd /Users/gillouche/workspace/projects/playground/docs && uv sync`
Expected: `.venv/` created, `uv.lock` generated, zensical/pyyaml/strawberry installed

- [ ] **Step 5: Verify zensical is available**

Run: `cd /Users/gillouche/workspace/projects/playground/docs && uv run zensical --version`
Expected: Version output confirming zensical is installed

- [ ] **Step 6: Commit**

```bash
git add docs/pyproject.toml docs/.python-version docs/.gitignore docs/uv.lock
git commit -m "docs: initialize docs/ as uv project with zensical"
```

---

### Task 2: Create Zensical configuration

**Files:**
- Create: `docs/zensical.toml`

- [ ] **Step 1: Create zensical.toml**

```toml
[project]
site_name = "Playground Docs"
site_description = "Documentation for the Playground homelab monorepo"
repo_url = "https://github.com/gillouche/playground"
docs_dir = "content"
site_dir = "site"

nav = [
    { "Home" = "index.md" },
    { "Getting Started" = "getting-started/index.md" },
    { "Common" = [
        "common/architecture.md",
        "common/build-system.md",
        "common/ci-cd.md",
        "common/templates.md",
        "common/releases.md",
        "common/local-development.md",
    ]},
    { "Apps" = [
        "apps/index.md",
        { "API Lab" = [
            "apps/api-lab/index.md",
            "apps/api-lab/python-rest-api.md",
            "apps/api-lab/python-grpc-api.md",
            "apps/api-lab/graphql-gateway.md",
            "apps/api-lab/database.md",
            "apps/api-lab/go-api.md",
            "apps/api-lab/ts-api.md",
            "apps/api-lab/rust-traffic-generator.md",
            { "API Reference" = [
                "apps/api-lab/api-reference/index.md",
                "apps/api-lab/api-reference/rest-api.md",
                "apps/api-lab/api-reference/grpc-api.md",
                "apps/api-lab/api-reference/graphql-api.md",
            ]},
            "apps/api-lab/operations.md",
        ]},
        { "Demo App" = [
            "apps/demo-app/index.md",
            "apps/demo-app/greeting-service.md",
            "apps/demo-app/infra-check-service.md",
            "apps/demo-app/traffic-generator.md",
            "apps/demo-app/operations.md",
        ]},
    ]},
    { "Troubleshooting" = "troubleshooting.md" },
]

[project.theme]
variant = "modern"
language = "en"

features = [
    "content.code.copy",
    "content.code.select",
    "content.tabs.link",
    "navigation.expand",
    "navigation.footer",
    "navigation.indexes",
    "navigation.instant",
    "navigation.sections",
    "navigation.tabs",
    "navigation.tabs.sticky",
    "navigation.top",
    "navigation.tracking",
    "search.highlight",
    "toc.follow",
]

[[project.theme.palette]]
media = "(prefers-color-scheme: light)"
scheme = "default"
primary = "indigo"
accent = "indigo"
toggle.icon = "lucide/sun"
toggle.name = "Switch to dark mode"

[[project.theme.palette]]
media = "(prefers-color-scheme: dark)"
scheme = "slate"
primary = "indigo"
accent = "indigo"
toggle.icon = "lucide/moon"
toggle.name = "Switch to light mode"

[project.theme.icon]
repo = "fontawesome/brands/github"

[project.markdown_extensions.admonition]
[project.markdown_extensions.attr_list]
[project.markdown_extensions.def_list]
[project.markdown_extensions.footnotes]
[project.markdown_extensions.md_in_html]

[project.markdown_extensions.toc]
permalink = true

[project.markdown_extensions.pymdownx.highlight]
anchor_linenums = true
line_spans = "__span"
pygments_lang_class = true

[project.markdown_extensions.pymdownx.inlinehilite]
[project.markdown_extensions.pymdownx.details]

[project.markdown_extensions.pymdownx.superfences]

[project.markdown_extensions.pymdownx.tabbed]
alternate_style = true
combine_header_slug = true

[project.markdown_extensions.pymdownx.tasklist]
custom_checkbox = true
```

- [ ] **Step 2: Create minimal content/index.md for testing**

```markdown
# Playground Docs

Welcome to the Playground documentation.
```

- [ ] **Step 3: Verify zensical serves the site**

Run: `cd /Users/gillouche/workspace/projects/playground/docs && uv run zensical serve & sleep 5 && curl -s http://localhost:8000 | head -20; kill %1`
Expected: HTML output containing "Playground Docs"

- [ ] **Step 4: Commit**

```bash
git add docs/zensical.toml docs/content/index.md
git commit -m "docs: add zensical configuration and minimal index page"
```

---

### Task 3: Create diagram generation pipeline

**Files:**
- Create: `docs/generate_diagrams.sh`
- Create: `docs/diagrams/api-lab-architecture.mmd`
- Create: `docs/diagrams/demo-app-architecture.mmd`
- Create: `docs/diagrams/release-flow.mmd`
- Create: `docs/diagrams/ci-pipeline.mmd`

- [ ] **Step 1: Create generate_diagrams.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIAGRAMS_DIR="${SCRIPT_DIR}/diagrams"
OUTPUT_DIR="${SCRIPT_DIR}/content/assets/diagrams"

mkdir -p "${OUTPUT_DIR}"

if ! command -v npx &>/dev/null; then
    echo "ERROR: npx not found. Node.js is required for mermaid-cli." >&2
    exit 1
fi

found=0
for mmd_file in "${DIAGRAMS_DIR}"/*.mmd; do
    [ -f "${mmd_file}" ] || continue
    found=1
    name="$(basename "${mmd_file}" .mmd)"
    output="${OUTPUT_DIR}/${name}.svg"
    echo "Rendering ${name}.mmd -> ${name}.svg"
    npx -y @mermaid-js/mermaid-cli mmdc -i "${mmd_file}" -o "${output}" -b transparent --quiet
done

if [ "${found}" -eq 0 ]; then
    echo "WARNING: No .mmd files found in ${DIAGRAMS_DIR}" >&2
fi
```

- [ ] **Step 2: Create api-lab-architecture.mmd**

Note: `.mmd` files contain raw mermaid syntax without markdown code fences. The content below is the exact file content.

```
graph TB
    subgraph Clients
        REST_CLIENT[REST Client]
        GRPC_CLIENT[gRPC Client]
        GQL_CLIENT[GraphQL Client]
        TRAFFIC[Rust Traffic Generator]
    end

    subgraph API Lab Services
        REST[Python REST API<br/>FastAPI :8080]
        GRPC[Python gRPC API<br/>asyncio :50051]
        GQL[GraphQL Gateway<br/>Strawberry :8083]
        GO[Go API<br/>Chi :8081<br/>planned]
        TS[TypeScript API<br/>Fastify :8082<br/>planned]
    end

    subgraph Shared
        SVC[BookService<br/>Business Logic]
        CACHE[Redis Cache<br/>TTL-based]
        DB[(PostgreSQL<br/>books, reservations)]
    end

    subgraph Observability
        PROM[Prometheus<br/>Metrics]
        OTEL[OpenTelemetry<br/>Traces]
    end

    REST_CLIENT --> REST
    GRPC_CLIENT --> GRPC
    GQL_CLIENT --> GQL
    TRAFFIC --> REST
    TRAFFIC --> GO
    TRAFFIC --> TS

    GQL -->|HTTP| REST

    REST --> SVC
    GRPC --> SVC

    SVC --> CACHE
    SVC --> DB
    CACHE --> DB

    REST --> PROM
    REST --> OTEL
    GRPC --> PROM
    GQL --> PROM
```

- [ ] **Step 3: Create demo-app-architecture.mmd**

Note: Raw mermaid syntax, no code fences in the actual file.

```
graph TB
    subgraph Demo App Services
        GREET[Greeting Service<br/>FastAPI :8080]
        INFRA[Infra Check Service<br/>FastAPI :8080]
        TGEN[Traffic Generator<br/>httpx async]
    end

    subgraph Infrastructure
        PG[(PostgreSQL)]
        REDIS[(Redis)]
        KAFKA[Kafka]
        MONGO[(MongoDB)]
    end

    subgraph Observability
        PROM[Prometheus]
        JAEGER[Jaeger<br/>Tracing]
    end

    TGEN -->|HTTP requests| GREET

    INFRA --> PG
    INFRA --> REDIS
    INFRA --> KAFKA
    INFRA --> MONGO

    GREET --> PROM
    GREET --> JAEGER
    INFRA --> PROM
    TGEN --> JAEGER
```

- [ ] **Step 4: Create release-flow.mmd**

Note: Raw mermaid syntax, no code fences in the actual file.

```
flowchart LR
    subgraph Build
        CI[CI Build] --> NEXUS[Push to Nexus]
    end

    subgraph Release
        NEXUS --> SYNC[sync_dev.py<br/>Update dev BOM]
        SYNC --> DEV[releases/dev/]
        DEV --> FREEZE[freeze.py<br/>Create version snapshot]
        FREEZE --> VER[releases/versions/v1.0.0.yaml]
    end

    subgraph Promote
        VER --> PTEST[promote.py --target test]
        PTEST --> TEST[releases/test/]
        TEST --> PPROD[promote.py --target prod]
        PPROD --> PROD[releases/prod/]
    end

    subgraph Rollback
        PROD --> RB[rollback.py<br/>Revert to previous version]
        RB --> PROD
    end
```

- [ ] **Step 5: Create ci-pipeline.mmd**

Note: Raw mermaid syntax, no code fences in the actual file.

```
flowchart TB
    PUSH[Push / PR] --> SEC[Security Check]

    SEC --> DEMO[demo-app<br/>Build & Test]
    SEC --> API[api-lab<br/>Build & Test]

    API --> SYS[system-test-api-lab<br/>Docker Compose infra<br/>Run migrations<br/>Start services<br/>pytest]

    DEMO --> FIN[Finalize]
    SYS --> FIN

    FIN --> CACHE[Push Nix Cache<br/>main only]
    FIN --> DISCORD[Discord Notification]

    subgraph Nightly
        CRON[Cron 02:00 UTC] --> TRIVY[Trivy Security Scan<br/>All OCI images]
    end

    subgraph On Tag Push
        TAG[Tag Push] --> RETAG[Retag image<br/>SHA to version]
        RETAG --> NOTIFY[Discord Notification]
    end
```

- [ ] **Step 6: Make generate_diagrams.sh executable and test**

Run: `chmod +x /Users/gillouche/workspace/projects/playground/docs/generate_diagrams.sh && cd /Users/gillouche/workspace/projects/playground/docs && ./generate_diagrams.sh`
Expected: 4 SVG files created in `content/assets/diagrams/`

- [ ] **Step 7: Verify SVG files exist**

Run: `ls -la /Users/gillouche/workspace/projects/playground/docs/content/assets/diagrams/`
Expected: `api-lab-architecture.svg`, `demo-app-architecture.svg`, `release-flow.svg`, `ci-pipeline.svg`

- [ ] **Step 8: Commit**

```bash
git add docs/generate_diagrams.sh docs/diagrams/
git commit -m "docs: add mermaid diagram sources and generation script"
```

---

### Task 4: Create API reference generation script

**Files:**
- Create: `docs/generate_api_docs.py`

- [ ] **Step 1: Create generate_api_docs.py**

```python
#!/usr/bin/env python3
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

    import subprocess

    gateway_dir = schema_module_path.parent.parent
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.path.insert(0, 'src'); "
                "from schema import graphql_schema; print(str(graphql_schema))",
            ],
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
```

- [ ] **Step 2: Test the script**

Run: `cd /Users/gillouche/workspace/projects/playground/docs && uv run python generate_api_docs.py`
Expected: OpenAPI and Protobuf succeed, GraphQL may need path adjustments. Generated files appear in `content/apps/api-lab/api-reference/`

- [ ] **Step 3: Verify generated content**

Run: `head -30 /Users/gillouche/workspace/projects/playground/docs/content/apps/api-lab/api-reference/rest-api.md`
Expected: Markdown with API endpoints, parameters, schemas

- [ ] **Step 4: Commit**

```bash
git add docs/generate_api_docs.py
git commit -m "docs: add API reference generation script for OpenAPI, protobuf, and GraphQL"
```

---

### Task 5: Create orchestrator script

**Files:**
- Create: `docs/generate.sh`

- [ ] **Step 1: Create generate.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACTION="${1:-serve}"

echo "=== Generating diagrams ==="
"${SCRIPT_DIR}/generate_diagrams.sh"

echo "=== Generating API reference ==="
python "${SCRIPT_DIR}/generate_api_docs.py"

case "${ACTION}" in
    serve)
        echo "=== Starting Zensical dev server ==="
        cd "${SCRIPT_DIR}"
        zensical serve
        ;;
    build)
        echo "=== Building static site ==="
        cd "${SCRIPT_DIR}"
        zensical build
        echo "Site built to ${SCRIPT_DIR}/site/"
        ;;
    *)
        echo "Usage: $0 {serve|build}" >&2
        exit 1
        ;;
esac
```

Note: This script is intended to be run via `uv run ./generate.sh serve`, so `python` and `zensical` are already on the PATH from the uv environment.

- [ ] **Step 2: Make executable**

Run: `chmod +x /Users/gillouche/workspace/projects/playground/docs/generate.sh`

- [ ] **Step 3: Commit**

```bash
git add docs/generate.sh
git commit -m "docs: add orchestrator script for diagram and API doc generation"
```

---

## Chunk 2: Common Documentation

### Task 6: Write home page and getting started

**Files:**
- Modify: `docs/content/index.md`
- Create: `docs/content/getting-started/index.md`

- [ ] **Step 1: Write index.md (home page)**

```markdown
# Playground

A polyglot monorepo for experimenting with distributed systems in a homelab environment. This project explores building the same services across multiple languages and protocols, with production-grade infrastructure including CI/CD, observability, and GitOps deployment.

## Tech Stack

| Category | Technologies |
|----------|-------------|
| Languages | Python, Go, Rust, TypeScript |
| Build System | Bazel (hermetic, multi-language) |
| Dev Environment | Nix flakes |
| Deployment | Kubernetes, ArgoCD, Argo Rollouts |
| Observability | Prometheus, OpenTelemetry, Jaeger, Grafana |
| Infrastructure | PostgreSQL, Redis, Kafka, MongoDB |
| Registry | Nexus (Docker + PyPI proxy) |

## Apps

### [API Lab](apps/api-lab/index.md)

A library book management system implemented across multiple API protocols (REST, gRPC, GraphQL) and languages (Python, Go, TypeScript). Includes a Rust traffic generator for load testing.

### [Demo App](apps/demo-app/index.md)

A set of Python microservices demonstrating basic patterns: a greeting service, an infrastructure connectivity checker, and a traffic generator.

## Quick Start

```bash
cd docs
uv sync
./generate.sh serve
```

For full setup instructions, see [Getting Started](getting-started/index.md).
```

- [ ] **Step 2: Write getting-started/index.md**

```markdown
# Getting Started

## Prerequisites

- [Nix](https://nixos.org/download/) with flakes enabled
- Git

## Development Environment

Enter the Nix development shell which provides all required tools (Bazel, Python, Go, Rust, Node.js, kubectl, etc.):

```bash
nix develop ./nix
```

For language-specific shells:

```bash
nix develop ./nix#bazel    # Bazel + base tools
nix develop ./nix#python   # Python + uv
nix develop ./nix#go       # Go
nix develop ./nix#rust     # Rust + Cargo
nix develop ./nix#node     # Node.js + pnpm
```

## Repository Layout

```
playground/
  apps/                    # Application source code
    api-lab/               # Multi-protocol library API
    demo-app/              # Python microservices demo
  tools/                   # Build macros, release scripts, CI helpers
  releases/                # Release BOMs (dev/test/prod versions)
  infra/                   # Infrastructure configs (sandbox, minikube)
  nix/                     # Nix flake and dev shell definitions
  docs/                    # This documentation site
```

## Building

Build all targets for a specific app:

```bash
bazel build //apps/demo-app/...
bazel build //apps/api-lab/...
```

## Testing

Run all tests for an app:

```bash
bazel test //apps/demo-app/...
bazel test //apps/api-lab/...
```

Run a specific service's tests:

```bash
bazel test //apps/api-lab/python-rest-api:python-rest-api_unit_test
```

## Local Infrastructure

Start local infrastructure (PostgreSQL, Redis, Kafka, MongoDB, Jaeger):

```bash
docker compose -f infra/sandbox/localhost/docker-compose.yaml up -d
```

## Running Services Locally

```bash
bazel run //apps/demo-app/greeting-service:greeting-service
bazel run //apps/api-lab/python-rest-api:python-rest-api
```

## Code Quality

Pre-commit hooks handle formatting, linting, and type checking across all languages. They run automatically on commit. To run manually:

```bash
pre-commit run --all-files
```
```

- [ ] **Step 3: Commit**

```bash
git add docs/content/index.md docs/content/getting-started/index.md
git commit -m "docs: add home page and getting started guide"
```

---

### Task 7: Write common section documentation

**Files:**
- Create: `docs/content/common/architecture.md`
- Create: `docs/content/common/build-system.md`
- Create: `docs/content/common/ci-cd.md`
- Create: `docs/content/common/templates.md`
- Create: `docs/content/common/releases.md`
- Create: `docs/content/common/local-development.md`

- [ ] **Step 1: Write architecture.md**

```markdown
# Architecture

## Overview

The Playground monorepo follows a polyglot microservices architecture. Each app is a self-contained set of services with its own deployment manifests, monitoring configuration, and test suites.

## Shared Patterns

### Build System (Bazel)

All services use Bazel for hermetic, reproducible builds. Language-specific macros in `tools/` abstract common patterns (library, binary, tests, OCI image, push).

### Development Environment (Nix)

Nix flakes provide reproducible development environments. A single `nix develop ./nix` command installs all required tools with pinned versions.

### Deployment (GitOps)

Services deploy to Kubernetes via Kustomize overlays. ArgoCD watches the repository and applies changes. Argo Rollouts handle canary deployments with automated analysis.

### Observability

All services expose Prometheus metrics, structured JSON logs, and optional OpenTelemetry traces. ServiceMonitor resources configure Prometheus scraping. Grafana dashboards are committed as code.

### Infrastructure

Local development uses Docker Compose for backing services (PostgreSQL, Redis, Kafka, MongoDB, Jaeger). The same services are available on Minikube via Kubernetes manifests.

## Security

- OCI images use distroless base images
- Containers run as non-root with read-only filesystems
- Network policies restrict inter-service communication
- Nightly Trivy scans check for vulnerabilities
- Pre-commit hooks detect secrets and private keys
```

- [ ] **Step 2: Write build-system.md**

```markdown
# Build System

## Bazel

The project uses Bazel for all builds, configured via `MODULE.bazel` and `.bazelrc`.

## Language Macros

Each language has a build macro in `tools/` that generates standard targets from a single definition.

### Python (`tools/python_defs.bzl`)

```python
python_application(
    name = "my-service",
    srcs = glob(["src/**/*.py"]),
    deps = [requirement("fastapi"), ...],
    unit_tests = glob(["tests/unit/**/*.py"]),
    integration_tests = glob(["tests/integration/**/*.py"]),
    test_deps = [dev_requirement("pytest"), ...],
)
```

Generated targets:

| Target | Description |
|--------|-------------|
| `my-service_lib` | Python library |
| `my-service` | Python binary (entrypoint) |
| `my-service_unit_test` | Unit tests (tag: `unit`) |
| `my-service_integration_test` | Integration tests (tag: `integration`) |
| `my-service_lint` | Ruff lint check |
| `my-service_image` | OCI container image |
| `my-service_push` | Push image to Nexus |
| `my-service_load` | Load image to local Docker |

Go (`tools/go_defs.bzl`), Rust (`tools/rust_defs.bzl`), and TypeScript (`tools/ts_defs.bzl`) follow the same pattern.

## Cross-Compilation

Build for specific architectures:

```bash
bazel build --config=arm64 //apps/demo-app/greeting-service:greeting-service_image
bazel build --config=amd64 //apps/demo-app/greeting-service:greeting-service_image
```

## Bazel Configuration

Key `.bazelrc` settings:

- Local disk cache: `~/.cache/bazel/disk_cache`
- CI remote cache: `http://bazel-remote-cache.seaweedfs.svc.cluster.local:8080`
- Test output: errors only in CI, all locally

## OCI Base Images

All base images are pinned in `MODULE.bazel` with multi-platform support (linux/arm64, linux/amd64):

| Language | Base Image |
|----------|-----------|
| Python | `python:3.14.3-distroless` |
| Go | `go:1.26.0-distroless` |
| TypeScript | `node:24.14.0` |
| Rust | `rust:1.94.0` |
```

- [ ] **Step 3: Write ci-cd.md**

```markdown
# CI/CD

## Overview

![CI Pipeline](../assets/diagrams/ci-pipeline.svg)

## GitHub Actions Workflows

### ci.yaml (Main Pipeline)

Triggered on every push and pull request. Runs security checks, builds, tests, and publishes images.

**Jobs:**

1. **security-check** - Gate for artifact access
2. **demo-app** (20 min timeout) - Build and test all demo-app services
3. **api-lab** (20 min timeout) - Build and test all api-lab services, push images to Nexus (main branch only)
4. **system-test-api-lab** (15 min timeout) - Start infrastructure via Docker Compose, run database migrations, start services, execute system tests
5. **finalize** - Push Nix cache (main only), send Discord notifications

Concurrency: `ci-{{ github.ref }}` - new pushes to the same branch cancel in-progress runs.

### release.yaml

Triggered on tag pushes matching `*/*/*` pattern (e.g., `demo-app/greeting-service/v0.0.1`).

Parses the tag to extract app, component, and version. Retags the Docker image from commit SHA to version tag in Nexus.

### sonarqube.yaml

Triggered on push to main or PR to main. Discovers all services dynamically, runs tests with coverage, and submits results to SonarQube.

### security-scan.yaml

Nightly cron (02:00 UTC). Discovers all OCI image targets, builds them, and runs Trivy vulnerability scanning. Results are aggregated and sent to Discord.

## Runners

All jobs run on self-hosted `playground-runner` pool using custom ARC (Actions Runner Controller) containers.
```

- [ ] **Step 4: Write templates.md**

```markdown
# Service Templates

Templates for creating new services in the monorepo. Each template provides a standard structure with BUILD.bazel, source code, tests, and deployment manifests.

## Available Templates

=== "Python"

    ```
    apps/<app>/<service>/
      src/
        main.py
      tests/
        unit/
          test_main.py
      BUILD.bazel
      requirements.in
      requirements_lock.txt
    ```

    Setup:
    ```bash
    cp -r docs/templates/python apps/<app>/<new-service>
    cd apps/<app>/<new-service>
    # Update BUILD.bazel name and dependencies
    # Generate lock file:
    uv pip compile requirements.in -o requirements_lock.txt
    ```

=== "Go"

    ```
    apps/<app>/<service>/
      main.go
      go.mod
      go.sum
      BUILD.bazel
    ```

    Setup:
    ```bash
    cp -r docs/templates/go apps/<app>/<new-service>
    cd apps/<app>/<new-service>
    go mod init github.com/gillouche/playground/apps/<app>/<new-service>
    ```

=== "Rust"

    ```
    apps/<app>/<service>/
      src/
        main.rs
      Cargo.toml
      Cargo.lock
      BUILD.bazel
    ```

=== "TypeScript"

    ```
    apps/<app>/<service>/
      src/
        index.ts
      package.json
      pnpm-lock.yaml
      tsconfig.json
      BUILD.bazel
    ```

## After Creating a Service

1. Add the pip hub entry in `MODULE.bazel` (Python only)
2. Add deployment manifests under `apps/<app>/deploy/`
3. Add the service to `tools/deploy/ytt_gen.sh`
4. Update Kustomize overlays for each environment
```

- [ ] **Step 5: Write releases.md**

```markdown
# Releases

![Release Flow](../assets/diagrams/release-flow.svg)

## Concepts

### Bill of Materials (BOM)

Each release is tracked as a YAML file containing exact image references (tag, commit SHA, full registry path, digest).

### Environments

| Environment | Path | Purpose |
|-------------|------|---------|
| dev | `releases/dev/` | Latest builds from CI |
| test | `releases/test/` | Pre-production validation |
| prod | `releases/prod/` | Production |
| sandbox | `releases/sandbox/` | Local testing |

### Version Snapshots

Immutable version records stored in `releases/versions/<app>/v1.0.0.yaml`. Created by the freeze tool from git tags.

## Workflow

### 1. Sync Dev

Pull latest component images from Nexus and update the dev BOM:

```bash
bazel run //tools:sync_dev -- --app demo-app
```

### 2. Freeze a Version

Create an immutable version snapshot from the current git tags:

```bash
bazel run //tools:freeze -- --app demo-app --version v1.0.1
```

### 3. Promote to Test

```bash
bazel run //tools:promote -- --app demo-app --version v1.0.1 --target test --commit
```

### 4. Promote to Production

```bash
bazel run //tools:promote -- --app demo-app --version v1.0.1 --target prod --commit
```

### 5. Rollback

Revert to the previously deployed version:

```bash
bazel run //tools:rollback -- --app demo-app --target prod --commit
```

For manual rollback to a specific version:

```bash
bazel run //tools:promote -- --app demo-app --version v1.0.0 --target prod
```
```

- [ ] **Step 6: Write local-development.md**

```markdown
# Local Development

## Environment Setup

Enter the Nix development shell:

```bash
nix develop ./nix
```

This provides Bazel, Python, Go, Rust, Node.js, kubectl, kustomize, and all other required tools.

## Local Infrastructure

Start backing services:

```bash
docker compose -f infra/sandbox/localhost/docker-compose.yaml up -d
```

This starts:

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Caching |
| Kafka | 9092/9093 | Event streaming |
| MongoDB | 27017 | Document store |
| Jaeger | 16686 (UI), 4317/4318 (OTLP) | Distributed tracing |

## Running Tests

```bash
bazel test //apps/<app>/...                    # All tests for an app
bazel test //apps/<app>/<service>:*_unit_test   # Unit tests only
bazel test --test_tag_filters=integration ...   # Integration tests only
```

## Running Services

```bash
bazel run //apps/<app>/<service>:<service>
```

## System Tests (API Lab)

System tests require infrastructure and all services running:

```bash
cd apps/api-lab
./system-tests/run.sh
```

This starts PostgreSQL and Redis, runs migrations, starts the REST API, gRPC API, and GraphQL gateway, then runs the pytest suite.

## Minikube Deployment

For testing Kubernetes manifests locally:

```bash
minikube start
bazel run //apps/demo-app:deploy_minikube
```

## Pre-commit Hooks

Run all quality checks manually:

```bash
pre-commit run --all-files
```

Hooks include: Ruff (Python), gofmt/golangci-lint (Go), rustfmt/clippy (Rust), Prettier (JS/TS), Buildifier (Bazel), Shellcheck (Shell), Yamllint (YAML), mypy (Python types).
```

- [ ] **Step 7: Commit**

```bash
git add docs/content/common/
git commit -m "docs: add common section (architecture, build system, CI/CD, templates, releases, local dev)"
```

---

## Chunk 3: API Lab Documentation

### Task 8: Write API Lab app documentation

**Files:**
- Create: `docs/content/apps/index.md`
- Create: `docs/content/apps/api-lab/index.md`
- Create: `docs/content/apps/api-lab/python-rest-api.md`
- Create: `docs/content/apps/api-lab/python-grpc-api.md`
- Create: `docs/content/apps/api-lab/graphql-gateway.md`
- Create: `docs/content/apps/api-lab/database.md`

- [ ] **Step 1: Write apps/index.md**

```markdown
# Apps

The Playground monorepo contains multiple applications, each exploring different aspects of distributed systems.

| App | Description | Status |
|-----|-------------|--------|
| [API Lab](api-lab/index.md) | Multi-protocol library book management API (REST, gRPC, GraphQL) | Active |
| [Demo App](demo-app/index.md) | Python microservices demonstrating basic patterns | Active |

Each app has its own deployment manifests, monitoring configuration, and test suites. Apps are independent and can be built, tested, and deployed separately.
```

- [ ] **Step 2: Write api-lab/index.md**

```markdown
# API Lab

A library book management system implemented across multiple API protocols and languages, exploring patterns for building distributed services.

## Architecture

![API Lab Architecture](../../assets/diagrams/api-lab-architecture.svg)

## Services

| Service | Protocol | Language | Port | Status |
|---------|----------|----------|------|--------|
| [Python REST API](python-rest-api.md) | REST (OpenAPI) | Python / FastAPI | 8080 | Implemented |
| [Python gRPC API](python-grpc-api.md) | gRPC | Python / asyncio | 50051 | Implemented |
| [GraphQL Gateway](graphql-gateway.md) | GraphQL | Python / Strawberry | 8083 | Implemented |
| [Go API](go-api.md) | REST | Go / Chi | 8081 | Planned |
| [TypeScript API](ts-api.md) | REST | TypeScript / Fastify | 8082 | Planned |
| [Rust Traffic Generator](rust-traffic-generator.md) | HTTP client | Rust | - | Planned |

## Shared Components

- **[Database](database.md):** PostgreSQL with custom SQL migration system
- **BookService:** Core business logic shared by Python REST and gRPC APIs
- **Redis Cache:** TTL-based caching with pattern invalidation
- **OpenAPI Spec:** Single spec generates models for all language implementations

## Key Design Decisions

**Shared business logic:** The Python REST and gRPC APIs share a `BookService` class that encapsulates all business operations. This prevents logic duplication and ensures consistency across protocols.

**GraphQL as gateway:** The GraphQL API does not access the database directly. It proxies the REST API via HTTP, demonstrating the gateway/BFF pattern.

**Row-level locking:** Book reservations use `SELECT ... FOR UPDATE` to prevent race conditions when decrementing available copies.

**Cache invalidation:** Write operations invalidate related cache keys using Redis pattern deletion. Read operations cache with varying TTLs (30s for lists, 60s for single items, 15s for inventory).
```

- [ ] **Step 3: Write python-rest-api.md**

```markdown
# Python REST API

The primary REST API implementation, built with FastAPI and following the OpenAPI specification.

## Overview

| Attribute | Value |
|-----------|-------|
| Framework | FastAPI |
| Port | 8080 |
| Path prefix | `/api/v1` |
| Source | `apps/api-lab/python-rest-api/` |

## Endpoints

### Books

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/books` | List books with optional filters |
| GET | `/api/v1/books/{book_id}` | Get a single book |
| POST | `/api/v1/books` | Create a new book |
| PUT | `/api/v1/books/{book_id}` | Update a book |
| DELETE | `/api/v1/books/{book_id}` | Delete a book |

**Query filters** on `GET /api/v1/books`: `available_only` (bool), `genre` (string), `author` (string), `search` (string).

### Reservations

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/reservations` | Create reservations (single or batch) |
| GET | `/api/v1/reservations` | List reservations with filters |
| GET | `/api/v1/reservations/{id}` | Get a single reservation |
| POST | `/api/v1/reservations/{id}/return` | Return a borrowed book |

**Query filters** on `GET /api/v1/reservations`: `user_id`, `status`, `book_id`.

### Inventory

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/inventory` | Get all books with available copies > 0 |

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/healthz` | Liveness probe |
| GET | `/ready` | Readiness probe (checks DB and Redis) |
| GET | `/info` | Service metadata (version, environment, git commit) |

## Configuration

All configuration is via environment variables (Pydantic Settings):

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DATABASE` | `api_lab` | Database name |
| `POSTGRES_USER` | `postgres` | Database user |
| `POSTGRES_PASSWORD` | `postgres` | Database password |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `LOG_LEVEL` | `INFO` | Log level |
| `ENABLE_TRACING` | `false` | Enable OpenTelemetry tracing |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | - | OTLP collector endpoint |

## Error Handling

| HTTP Status | Condition |
|-------------|-----------|
| 404 | Resource not found |
| 409 | Duplicate ISBN or unavailable book for reservation |
| 500 | Internal server error |

## Observability

**Metrics** (Prometheus, via `/metrics`):

- `books_created_total` - Counter
- `reservations_created_total` - Counter
- `reservations_returned_total` - Counter
- `cache_hits_total{operation}` - Counter per operation
- `cache_misses_total{operation}` - Counter per operation
- `db_query_duration_seconds{operation}` - Histogram
- `cache_op_duration_seconds{operation}` - Histogram
- `books_available` - Gauge (total available copies)
- `active_reservations` - Gauge

**Logging:** Structured JSON with trace context (trace_id, span_id) via loguru.

**Tracing:** Optional OpenTelemetry with OTLP exporter, FastAPI auto-instrumentation.

## Resilience

- **Retry:** Tenacity-based exponential backoff (3 attempts, 0.5s-5s) for transient errors
- **Circuit Breaker:** Three-state FSM (closed/open/half-open) with configurable thresholds (5 failures, 30s recovery)

## Running

```bash
bazel run //apps/api-lab/python-rest-api:python-rest-api
```

## Testing

```bash
bazel test //apps/api-lab/python-rest-api:python-rest-api_unit_test
```

For the full auto-generated API reference, see [REST API Reference](api-reference/rest-api.md).
```

- [ ] **Step 4: Write python-grpc-api.md**

```markdown
# Python gRPC API

A gRPC server implementing the same library service as the REST API, using asyncio and JSON serialization.

## Overview

| Attribute | Value |
|-----------|-------|
| Framework | grpc.aio (asyncio) |
| Port | 50051 |
| Service | `library.v1.LibraryService` |
| Source | `apps/api-lab/python-grpc-api/` |

## RPC Methods

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `ListBooks` | `ListBooksRequest` | `ListBooksResponse` | List with filters |
| `GetBook` | `GetBookRequest` | `BookResponse` | Single book |
| `CreateBook` | `CreateBookRequest` | `BookResponse` | Create new book |
| `UpdateBook` | `UpdateBookRequest` | `BookResponse` | Partial update |
| `DeleteBook` | `DeleteBookRequest` | `Empty` | Delete book |
| `GetInventory` | `Empty` | `InventoryResponse` | Available books |
| `ReserveBooks` | `ReserveBooksRequest` | `ReserveBooksResponse` | Create reservations |
| `ReturnReservation` | `ReturnReservationRequest` | `ReservationResponse` | Return borrowed book |
| `ListReservations` | `ListReservationsRequest` | `ListReservationsResponse` | List with filters |
| `GetReservation` | `GetReservationRequest` | `ReservationResponse` | Single reservation |

## Implementation Details

The gRPC server uses a `GenericRpcHandler` with JSON serialization rather than generated protobuf stubs. Request and response bodies are JSON-encoded, allowing the same `BookService` business logic layer to be shared with the REST API.

gRPC reflection is enabled for service discovery.

## Error Handling

| gRPC Status | Condition |
|-------------|-----------|
| `NOT_FOUND` | Resource does not exist |
| `FAILED_PRECONDITION` | Business rule violation (e.g., unavailable book) |
| `INTERNAL` | Unexpected server error |

## Configuration

Same environment variables as the REST API (shared `Config` class from python-common).

The gRPC port is controlled by `GRPC_PORT` (default: `50051`).

## Running

```bash
bazel run //apps/api-lab/python-grpc-api:python-grpc-api
```

## Testing

```bash
bazel test //apps/api-lab/python-grpc-api:python-grpc-api_unit_test
```

For the full auto-generated API reference, see [gRPC API Reference](api-reference/grpc-api.md).
```

- [ ] **Step 5: Write graphql-gateway.md**

```markdown
# GraphQL Gateway

A GraphQL API that proxies the REST API, built with Strawberry and FastAPI. Demonstrates the gateway/BFF (Backend for Frontend) pattern.

## Overview

| Attribute | Value |
|-----------|-------|
| Framework | Strawberry + FastAPI |
| Port | 8083 |
| Endpoint | `/graphql` |
| Source | `apps/api-lab/graphql-gateway/` |

## Architecture

The GraphQL gateway does not access the database directly. It uses an HTTP client (`LibraryClient`) to forward requests to the Python REST API. This pattern allows the GraphQL layer to aggregate, reshape, and filter data for frontend consumers without duplicating business logic.

GraphiQL (interactive explorer) is enabled in non-production environments.

## Queries

| Query | Arguments | Returns |
|-------|-----------|---------|
| `books` | `available_only`, `genre`, `author`, `search` | `[BookType]` |
| `book` | `book_id` | `BookType` |
| `inventory` | - | `[BookType]` |
| `reservations` | `user_id`, `status`, `book_id` | `[ReservationType]` |
| `reservation` | `reservation_id` | `ReservationType` |

## Mutations

| Mutation | Arguments | Returns |
|----------|-----------|---------|
| `create_book` | `isbn`, `title`, `author`, `genre`, `published_year`, `total_copies` | `BookType` |
| `update_book` | `book_id`, optional fields | `BookType` |
| `delete_book` | `book_id` | `Boolean` |
| `reserve_books` | `user_id`, `book_ids` | `[ReservationType]` |
| `return_reservation` | `reservation_id` | `ReservationType` |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REST_API_URL` | `http://localhost:8080` | Target REST API base URL |

## Running

```bash
bazel run //apps/api-lab/graphql-gateway:graphql-gateway
```

## Testing

```bash
bazel test //apps/api-lab/graphql-gateway:graphql-gateway_unit_test
```

For the full auto-generated API reference, see [GraphQL API Reference](api-reference/graphql-api.md).
```

- [ ] **Step 6: Write database.md**

```markdown
# Database

PostgreSQL database with a custom SQL-based migration system.

## Schema

### books

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | Primary key, auto-generated |
| `isbn` | VARCHAR(13) | Unique, not null |
| `title` | TEXT | Not null |
| `author` | TEXT | Not null |
| `genre` | VARCHAR(100) | Not null |
| `published_year` | INTEGER | Not null |
| `total_copies` | INTEGER | Not null |
| `available_copies` | INTEGER | Not null, >= 0 |
| `created_at` | TIMESTAMPTZ | Default: now() |
| `updated_at` | TIMESTAMPTZ | Default: now() |

Indexes: `isbn`, `author`

### reservations

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | Primary key, auto-generated |
| `book_id` | UUID | Foreign key to books.id |
| `user_id` | VARCHAR(255) | Not null |
| `reserved_at` | TIMESTAMPTZ | Default: now() |
| `due_date` | TIMESTAMPTZ | Not null |
| `returned_at` | TIMESTAMPTZ | Nullable |
| `status` | reservation_status | Default: ACTIVE |

Indexes: `user_id`, `status`, `book_id`

`reservation_status` enum: `ACTIVE`, `RETURNED`, `OVERDUE`

### schema_migrations

Used internally by the migration runner to track applied migrations with checksum validation.

## Migration System

The migration runner (`database/migrate.py`) applies SQL files from `database/migrations/` in order. Migrations follow the naming convention `V{version:03d}__{description}.sql`.

Features:

- Tracks applied migrations with SHA-256 checksums
- Prevents modification of already-applied migrations
- Supports `--check` mode for CI (exits 1 if pending migrations exist)
- Uses asyncpg for direct PostgreSQL connections

### Running Migrations

```bash
python apps/api-lab/database/migrate.py
```

Verify all migrations are applied:

```bash
python apps/api-lab/database/migrate.py --check
```

### Creating a New Migration

Add a SQL file to `apps/api-lab/database/migrations/`:

```
V002__add_categories_table.sql
```

The version number must be sequential. The migration runner will apply it on the next run.

## Connection Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | Database host |
| `POSTGRES_PORT` | `5432` | Database port |
| `POSTGRES_DATABASE` | `api_lab` | Database name |
| `POSTGRES_USER` | `postgres` | Username |
| `POSTGRES_PASSWORD` | `postgres` | Password |

## SQLAlchemy ORM

The Python services use SQLAlchemy with async support (`asyncpg` driver). Models are defined in `python-common/src/database/models.py`. Connection pooling is configured with `pool_size=5` and `max_overflow=10`.
```

- [ ] **Step 7: Commit**

```bash
git add docs/content/apps/
git commit -m "docs: add API Lab documentation (overview, REST, gRPC, GraphQL, database)"
```

---

### Task 9: Write API Lab stub services and operations

**Files:**
- Create: `docs/content/apps/api-lab/go-api.md`
- Create: `docs/content/apps/api-lab/ts-api.md`
- Create: `docs/content/apps/api-lab/rust-traffic-generator.md`
- Create: `docs/content/apps/api-lab/api-reference/index.md`
- Create: `docs/content/apps/api-lab/operations.md`

- [ ] **Step 1: Write go-api.md**

```markdown
# Go API

!!! info "Planned"
    This service is scaffolded but not yet implemented. The generated server stubs return 501 Not Implemented for all endpoints.

REST API implementation in Go, targeting the same OpenAPI specification as the Python REST API.

## Overview

| Attribute | Value |
|-----------|-------|
| Framework | Chi router (planned) |
| Port | 8081 |
| Source | `apps/api-lab/go-api/` |

## Current State

- HTTP server with signal handling
- Generated models and server stubs from OpenAPI spec
- All endpoints return 501 Not Implemented

## Suggested Libraries

| Purpose | Library |
|---------|---------|
| HTTP Router | `go-chi/chi/v5` |
| PostgreSQL | `jackc/pgx/v5` |
| Redis | `redis/go-redis/v9` |
| gRPC | `google.golang.org/grpc` |
| GraphQL | `99designs/gqlgen` |
| Observability | `go.opentelemetry.io/otel` |
| Metrics | `prometheus/client_golang` |
| Logging | `log/slog` (stdlib) |
| Circuit Breaker | `sony/gobreaker` |

## Getting Started with Implementation

1. Implement the `BookService` interface with pgx for database access
2. Wire up Chi router handlers to call the service
3. Add Redis caching layer
4. Add Prometheus metrics and OpenTelemetry tracing
5. Write table-driven unit tests
6. Add integration tests with real PostgreSQL
```

- [ ] **Step 2: Write ts-api.md**

```markdown
# TypeScript API

!!! info "Planned"
    This service is scaffolded but not yet implemented. All endpoints return "Not implemented".

REST API implementation in TypeScript with Fastify, targeting the same OpenAPI specification.

## Overview

| Attribute | Value |
|-----------|-------|
| Framework | Fastify 5.x |
| Port | 8082 |
| Source | `apps/api-lab/ts-api/` |

## Current State

- Fastify server with CORS and signal handling
- Generated types and server interface from OpenAPI spec
- All endpoints return "Not implemented"

## Suggested Libraries

| Purpose | Library |
|---------|---------|
| PostgreSQL | `pg` or `prisma` |
| Redis | `ioredis` |
| gRPC | `@grpc/grpc-js` |
| GraphQL | `Apollo Server` + `@as-integrations/fastify` |
| Observability | `@opentelemetry/sdk-node` |
| Metrics | `prom-client` |
| Logging | `pino` (Fastify default) |
| Circuit Breaker | `opossum` |

## Getting Started with Implementation

1. Set up database connection with pg or Prisma
2. Implement route handlers calling the database
3. Add Redis caching
4. Add Prometheus metrics endpoint
5. Add OpenTelemetry instrumentation
6. Write tests with Vitest or Jest
```

- [ ] **Step 3: Write rust-traffic-generator.md**

```markdown
# Rust Traffic Generator

!!! info "Planned"
    This service is scaffolded but not yet implemented. Currently only reads target URLs from environment variables.

Load and stress testing tool for the library API, targeting all three language implementations.

## Overview

| Attribute | Value |
|-----------|-------|
| Language | Rust |
| Source | `apps/api-lab/rust-traffic-generator/` |

## Current State

Minimal scaffolding that accepts target URLs via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PYTHON_API_URL` | `http://localhost:8080` | Python API target |
| `GO_API_URL` | `http://localhost:8081` | Go API target |
| `TS_API_URL` | `http://localhost:8082` | TypeScript API target |

## Planned Workflow

1. List books (`GET /api/v1/books`)
2. Create a book with random data
3. Reserve the book
4. Return the reservation
5. Check inventory
6. Delete the book

## Suggested Implementation

| Component | Crate |
|-----------|-------|
| Async runtime | `tokio` |
| HTTP client | `reqwest` with connection pooling |
| Serialization | `serde` + `serde_json` |
| Random data | `rand` |
| Metrics | `prometheus` crate + `/metrics` endpoint |
| Tracing | `opentelemetry` + `tracing` |

Key features to implement: configurable concurrency, token bucket rate limiting, per-API request metrics (counters, histograms).
```

- [ ] **Step 4: Write api-reference/index.md**

```markdown
# API Reference

Auto-generated API reference documentation for all API Lab protocols.

| Protocol | Source | Documentation |
|----------|--------|---------------|
| REST | `apps/api-lab/openapi/openapi.yaml` | [REST API Reference](rest-api.md) |
| gRPC | `apps/api-lab/openapi/proto/library/v1/library.proto` | [gRPC API Reference](grpc-api.md) |
| GraphQL | `apps/api-lab/graphql-gateway/src/schema.py` | [GraphQL API Reference](graphql-api.md) |

These pages are generated by `docs/generate_api_docs.py` and should not be edited manually.

To regenerate:

```bash
cd docs
uv run python generate_api_docs.py
```
```

- [ ] **Step 5: Write operations.md**

```markdown
# API Lab Operations

## System Tests

End-to-end tests that validate all three API protocols (REST, gRPC, GraphQL) and cross-protocol data consistency.

### Running Locally

```bash
cd apps/api-lab
./system-tests/run.sh
```

This script:

1. Starts PostgreSQL and Redis via Docker Compose
2. Runs database migrations
3. Starts the REST API, gRPC API, and GraphQL gateway
4. Executes the pytest system test suite
5. Cleans up

### Test Suites

| Suite | Description |
|-------|-------------|
| `test_full_lifecycle.py` | Complete CRUD + reservation workflow |
| `test_rest_*.py` | REST endpoint validation |
| `test_graphql.py` | GraphQL queries and mutations |
| `test_grpc.py` | gRPC method invocations |
| `test_cross_protocol.py` | Data consistency across REST, gRPC, GraphQL |

### CI Integration

System tests run in CI after the api-lab build job succeeds. Docker Compose starts PostgreSQL and Redis, migrations run, services start, and the test suite executes.

## Monitoring

### Prometheus Alerts

Defined in `apps/api-lab/monitoring/deploy/templates/prometheus-rules.yaml`:

| Alert | Condition | Severity |
|-------|-----------|----------|
| `ApiLabHighErrorRate` | 5xx errors > 5% for 5 minutes | Warning |
| `ApiLabHighLatency` | P95 latency > 1 second for 5 minutes | Warning |
| `ApiLabCircuitBreakerOpen` | Circuit breaker in open state | Critical |
| `ApiLabRestartLoop` | Container restarts > 3 in 1 hour | Critical |

### Metrics Endpoints

All Python services expose Prometheus metrics at `/metrics` via `prometheus-fastapi-instrumentator`.

### Deployment

Services deploy via Kustomize overlays with environment-specific patches. Production deployments use Argo Rollouts with canary strategy (20% -> 40% -> 60% -> 80% with analysis).

Each service has:

- Rollout manifest (canary strategy)
- ConfigMap (environment-specific settings)
- Ingress rule
- ServiceMonitor (Prometheus scraping)
- ScaledObject (KEDA autoscaling)
- NetworkPolicy (egress rules for database/Redis)
```

- [ ] **Step 6: Commit**

```bash
git add docs/content/apps/api-lab/
git commit -m "docs: add API Lab stub services, API reference index, and operations"
```

---

## Chunk 4: Demo App Documentation and Finishing

### Task 10: Write Demo App documentation

**Files:**
- Create: `docs/content/apps/demo-app/index.md`
- Create: `docs/content/apps/demo-app/greeting-service.md`
- Create: `docs/content/apps/demo-app/infra-check-service.md`
- Create: `docs/content/apps/demo-app/traffic-generator.md`
- Create: `docs/content/apps/demo-app/operations.md`

- [ ] **Step 1: Write demo-app/index.md**

```markdown
# Demo App

A set of Python microservices demonstrating basic patterns for building, testing, and deploying services in the Playground monorepo.

## Architecture

![Demo App Architecture](../../assets/diagrams/demo-app-architecture.svg)

## Services

| Service | Description | Port |
|---------|-------------|------|
| [Greeting Service](greeting-service.md) | Returns personalized greetings | 8080 |
| [Infra Check Service](infra-check-service.md) | Tests connectivity to backend infrastructure | 8080 |
| [Traffic Generator](traffic-generator.md) | Sends continuous load to the greeting service | - |

## Tech Stack

All services are built with FastAPI and share common patterns:

- Prometheus metrics via `prometheus-fastapi-instrumentator`
- OpenTelemetry tracing with OTLP exporter to Jaeger
- Structured logging
- Graceful shutdown via signal handlers
- Distroless container images running as non-root
```

- [ ] **Step 2: Write greeting-service.md**

```markdown
# Greeting Service

A simple HTTP service that returns personalized greetings. Serves as the baseline example for the monorepo's service patterns.

## Overview

| Attribute | Value |
|-----------|-------|
| Framework | FastAPI |
| Port | 8080 |
| Source | `apps/demo-app/greeting-service/` |

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Returns greeting for the given `name` query parameter |
| GET | `/healthz` | Liveness probe |
| GET | `/ready` | Readiness probe |
| GET | `/info` | Service metadata |
| GET | `/metrics` | Prometheus metrics |

The greeting response includes the current environment name: "Hello, {name}! Welcome to the Playground ({environment})."

User input is HTML-escaped to prevent XSS.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Log level |
| `ENABLE_TRACING` | `false` | Enable OpenTelemetry |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | - | OTLP collector endpoint |
| `NAMESPACE` | - | Kubernetes namespace |
| `ENVIRONMENT` | - | Environment name (shown in greeting) |
| `APP_VERSION` | - | Application version |

## Deployment

Canary deployment via Argo Rollouts:

- Steps: 20% -> 40% -> 60% -> 80%
- Analysis: success-rate and error-rate templates
- Pauses: 30s after first step, 10s between subsequent steps

Resource limits: 256Mi memory, 100m CPU (request) / 512Mi memory, 200m CPU (limit).

Targets Raspberry Pi nodes (`topology.kubernetes.io/node-group: rpi`).

## Running

```bash
bazel run //apps/demo-app/greeting-service:greeting-service
```

## Testing

```bash
bazel test //apps/demo-app/greeting-service:greeting-service_unit_test
```
```

- [ ] **Step 3: Write infra-check-service.md**

```markdown
# Infra Check Service

A multi-backend verification service that tests connectivity to PostgreSQL, Redis, Kafka, and MongoDB.

## Overview

| Attribute | Value |
|-----------|-------|
| Framework | FastAPI |
| Port | 8080 |
| Source | `apps/demo-app/infra-check-service/` |

## Endpoints

Each backend has read/write and health endpoints:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/postgres` | Read/write test to PostgreSQL |
| GET | `/postgres/health` | PostgreSQL connectivity check |
| GET | `/redis` | Get/set test to Redis |
| GET | `/redis/health` | Redis connectivity check |
| GET | `/kafka` | Produce/consume test to Kafka |
| GET | `/kafka/health` | Kafka connectivity check |
| GET | `/mongodb` | Insert/find test to MongoDB |
| GET | `/mongodb/health` | MongoDB connectivity check |
| GET | `/ready` | Readiness (fails if any backend unhealthy) |
| GET | `/metrics` | Prometheus metrics |

## Configuration

Configuration via environment variables or `config.yaml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka brokers |
| `MONGODB_HOST` | `localhost` | MongoDB host |
| `MONGODB_PORT` | `27017` | MongoDB port |

## Clients

Each backend has a dedicated async client:

- **PostgreSQL:** asyncpg with SQLAlchemy URL building
- **Redis:** redis-py async client
- **Kafka:** aiokafka producer/consumer
- **MongoDB:** Motor async client

## Running

```bash
bazel run //apps/demo-app/infra-check-service:infra-check-service
```

Requires local infrastructure running (see [Local Development](../../common/local-development.md)).
```

- [ ] **Step 4: Write traffic-generator.md**

```markdown
# Traffic Generator

An async HTTP load generator that sends continuous requests to the greeting service.

## Overview

| Attribute | Value |
|-----------|-------|
| Framework | httpx (async) |
| Source | `apps/demo-app/traffic-generator-service/` |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TARGET_URL` | `http://greeting-service:8080` | Target service URL |
| `CONCURRENCY` | `10` | Number of concurrent workers |
| `ENABLE_TRACING` | `true` | Enable OpenTelemetry tracing |

## Behavior

1. Waits for the target service to become healthy (polls `/healthz`)
2. Spawns configured number of async workers
3. Each worker sends continuous HTTP requests with 10ms sleep between requests
4. Request timeout: 5 seconds
5. Graceful shutdown on SIGTERM/SIGINT

OpenTelemetry httpx instrumentation propagates trace context to the greeting service, enabling end-to-end trace visibility in Jaeger.

## Running

```bash
bazel run //apps/demo-app/traffic-generator-service:traffic-generator-service
```

Requires the greeting service to be running at the configured `TARGET_URL`.
```

- [ ] **Step 5: Write demo-app/operations.md**

```markdown
# Demo App Operations

## Deployment

All three services deploy via Kustomize with environment-specific overlays at `apps/demo-app/deploy/{dev,test,prod}/`.

### Canary Strategy

Services use Argo Rollouts with canary deployment:

1. Route 20% of traffic to new version, wait 30s, run analysis
2. Increase to 40%, wait 10s
3. Increase to 60%, wait 10s
4. Increase to 80%, wait 10s
5. Full rollout

Analysis templates check success rate and error rate against Prometheus metrics.

### Resources

| Service | Memory (request/limit) | CPU (request/limit) |
|---------|----------------------|---------------------|
| Greeting Service | 256Mi / 512Mi | 100m / 200m |
| Infra Check Service | 256Mi / 512Mi | 100m / 200m |
| Traffic Generator | 128Mi / 256Mi | 50m / 100m |

### Network Policies

- Ingress: allowed from ingress controller
- Egress (infra-check only): allowed to PostgreSQL, Redis, Kafka, MongoDB

### Autoscaling

KEDA ScaledObjects configured for HTTP-based autoscaling.

## Monitoring

### Grafana Dashboard

A Grafana dashboard is deployed as a ConfigMap at `apps/demo-app/deploy/{env}/monitoring-grafana-dashboard.yaml`.

### ServiceMonitors

Each service has a Prometheus ServiceMonitor that scrapes the `/metrics` endpoint.

### Tracing

OpenTelemetry traces are exported to Jaeger via OTLP. The traffic generator propagates trace context to the greeting service, enabling end-to-end request tracing.
```

- [ ] **Step 6: Commit**

```bash
git add docs/content/apps/demo-app/
git commit -m "docs: add Demo App documentation (all services and operations)"
```

---

### Task 11: Write troubleshooting page and update root README

**Files:**
- Create: `docs/content/troubleshooting.md`
- Modify: `README.md` (repo root)

- [ ] **Step 1: Write troubleshooting.md**

```markdown
# Troubleshooting

## Nix

### "experimental-features" error

If `nix develop` fails with an error about experimental features, enable flakes:

```bash
echo "experimental-features = nix-command flakes" >> ~/.config/nix/nix.conf
```

### Shell doesn't have expected tools

Make sure you're using the default shell which includes all tools:

```bash
nix develop ./nix
```

Language-specific shells (e.g., `./nix#python`) only include that language's tools.

## Bazel

### Remote cache connection failures

If CI builds fail with remote cache errors, they fall back to local builds automatically. The remote cache runs on `bazel-remote-cache.seaweedfs.svc.cluster.local:8080`.

For local development, the disk cache at `~/.cache/bazel/disk_cache` is always used.

### Stale build artifacts

```bash
bazel clean --expunge
```

### Python dependency resolution failures

If pip resolution fails during `bazel build`, regenerate the lock file:

```bash
cd apps/<app>
uv pip compile requirements.in -o requirements_lock.txt
```

## Docker / Containers

### Cannot pull base images

Base images are proxied through Nexus. If the Nexus CA is not trusted, you may see TLS errors. The Nix shell sets up the CA bundle automatically.

### Image build fails on ARM

Ensure you're using the correct platform config:

```bash
bazel build --config=arm64 //apps/...
```

## Tests

### System tests fail to connect

Ensure infrastructure is running:

```bash
docker compose -f infra/sandbox/localhost/docker-compose.yaml up -d
```

Check service health:

```bash
curl http://localhost:8080/healthz
curl http://localhost:8083/graphql   # GraphQL
```

### Pre-commit hooks fail

Run hooks manually to see detailed output:

```bash
pre-commit run --all-files --verbose
```

Common issues:

- **Ruff:** formatting or lint errors in Python code
- **mypy:** type errors (check `pyproject.toml` for configuration)
- **gofmt:** Go formatting (auto-fixed by the hook)
- **Buildifier:** Bazel file formatting (auto-fixed by the hook)
```

- [ ] **Step 2: Update root README.md**

Read the current `README.md` first, then replace its content with a slimmed-down version that points to the docs site. The new README should contain:

```markdown
# Playground

A polyglot monorepo for experimenting with distributed systems in a homelab environment.

Built with Python, Go, Rust, and TypeScript. Uses Bazel for builds, Nix for development environments, and GitOps for deployment.

## Documentation

Full documentation is available as a local website:

```bash
cd docs
uv sync
./generate.sh serve
```

Then open [http://localhost:8000](http://localhost:8000).

## Quick Start

```bash
nix develop ./nix          # Enter dev environment
bazel test //apps/...      # Run all tests
```

## Apps

| App | Description |
|-----|-------------|
| [api-lab](apps/api-lab/) | Multi-protocol library API (REST, gRPC, GraphQL) in Python, Go, TypeScript |
| [demo-app](apps/demo-app/) | Python microservices demo (greeting, infra-check, traffic generator) |
```

- [ ] **Step 3: Commit**

```bash
git add docs/content/troubleshooting.md README.md
git commit -m "docs: add troubleshooting guide and update root README to point to docs site"
```

---

### Task 12: Remove old documentation and final verification

**Files:**
- Remove: `docs/runbooks/` (content migrated to `docs/content/common/`)
- Remove: `docs/templates/` (content migrated to `docs/content/common/templates.md`)

- [ ] **Step 1: Remove old docs directories**

```bash
git rm -r docs/runbooks/ docs/templates/
```

- [ ] **Step 2: Run full generation pipeline**

Run: `cd /Users/gillouche/workspace/projects/playground/docs && ./generate.sh build`
Expected: Diagrams generated, API docs generated, site built to `docs/site/`

- [ ] **Step 3: Verify site serves correctly**

Run: `cd /Users/gillouche/workspace/projects/playground/docs && ./generate.sh serve &; sleep 5; curl -s http://localhost:8000 | grep "Playground"; kill %1`
Expected: Site serves with all pages accessible

- [ ] **Step 4: Verify navigation works**

Manually check key pages in browser at `http://localhost:8000`:

- Home page loads
- Getting Started page
- Common > Architecture (with diagram)
- Apps > API Lab > Python REST API
- Apps > Demo App > Greeting Service
- Troubleshooting
- API Reference > REST API (auto-generated)

- [ ] **Step 5: Commit removal of old docs**

```bash
git commit -m "docs: remove old runbooks and templates (migrated to docs site)"
```

- [ ] **Step 6: Fix any issues found during verification**

If any pages show broken links, missing images, or rendering errors:
1. Check `zensical serve` stderr output for warnings
2. Fix broken image paths (SVGs should be at `../assets/diagrams/<name>.svg` relative to the page)
3. Fix any nav entries in `zensical.toml` that don't match actual file paths
4. Re-run `./generate.sh build` and verify no errors
5. Commit fixes if any were needed
