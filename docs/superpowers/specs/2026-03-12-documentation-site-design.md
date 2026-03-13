# Documentation Site Design Spec

## Overview

Build a comprehensive documentation website for the Playground monorepo using Zensical (static site generator by the creator of Material for MkDocs). The site serves both developers and ops, is local-only, and organizes content by app with shared common sections.

## Audience

Internal developers and ops/platform team working in this homelab playground monorepo.

## Tool Choice

Zensical — installed via uv, configured with `zensical.toml`, generates a searchable responsive static site from markdown. Chosen for its simplicity, Material for MkDocs compatibility, and built-in search/theming.

## Architecture

Standalone documentation setup decoupled from Bazel. The `docs/` directory is its own uv Python project with a `pyproject.toml`. A shell script (`docs/generate.sh`) orchestrates API spec extraction and Zensical build/serve. No Bazel integration — docs are a content-authoring concern, not a build artifact.

## Directory Structure

```
docs/
  pyproject.toml                  # uv project: zensical + pyyaml dependencies
  uv.lock                        # Locked dependencies
  .python-version                 # Python version pin
  zensical.toml                   # Site configuration
  generate.sh                    # API spec extraction + build/serve
  generate_api_docs.py            # Python script to convert specs to markdown
  generate_diagrams.sh            # Renders .mmd files to SVG via mmdc (mermaid-cli)
  .gitignore                      # Ignore generated API reference files + .venv
  diagrams/                        # Mermaid source files (.mmd)
    api-lab-architecture.mmd
    demo-app-architecture.mmd
    release-flow.mmd
    ci-pipeline.mmd
  content/
    assets/
      diagrams/                   # Generated SVGs (gitignored)
        api-lab-architecture.svg
        demo-app-architecture.svg
        release-flow.svg
        ci-pipeline.svg
    index.md                      # Home page
    getting-started/
      index.md                    # Nix setup, Bazel basics, repo conventions
    common/
      architecture.md             # Shared infra patterns (Bazel, Nix, GitOps)
      build-system.md             # Bazel macros, target conventions, .bazelrc
      ci-cd.md                    # GitHub Actions workflows
      templates.md                # Service templates (Python, Go, Rust, TS)
      releases.md                 # Release/promotion workflow (dev->test->prod)
      local-development.md        # Common dev workflow
    apps/
      index.md                    # Apps overview
      api-lab/
        index.md                  # API-lab overview, architecture, service map
        python-rest-api.md
        python-grpc-api.md
        graphql-gateway.md
        database.md               # Schema, migrations
        go-api.md                 # Stub (skeleton service)
        ts-api.md                 # Stub (skeleton service)
        rust-traffic-generator.md # Stub (skeleton service)
        api-reference/
          index.md                # Auto-gen overview
          rest-api.md             # Generated from OpenAPI spec
          grpc-api.md             # Generated from protobuf
          graphql-api.md          # Generated from GraphQL schema
        operations.md             # System tests, monitoring, deploy manifests
      demo-app/
        index.md                  # Demo-app overview, architecture
        greeting-service.md
        infra-check-service.md
        traffic-generator.md
        operations.md             # Monitoring, deployment
    troubleshooting.md            # Common issues across all apps
```

New apps add a folder under `docs/content/apps/` following the same pattern.

### Existing `docs/` contents

The current `docs/runbooks/` and `docs/templates/` directories will be removed after their content is migrated into the new structure. `docs/superpowers/` remains as-is (unrelated to the documentation site).

### Generated file management

Generated files are gitignored and regenerated on every `generate.sh` run:
- API reference markdown: `docs/content/apps/api-lab/api-reference/*.md` (except `index.md` which is hand-written and tracked)
- Diagram SVGs: `docs/content/assets/diagrams/*.svg`

## Python Environment (uv project)

The `docs/` directory is a standalone uv project:

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
```

`strawberry-graphql` is needed to export the GraphQL schema SDL for doc generation.

Usage:
```bash
cd docs
uv sync          # install dependencies
uv run ./generate.sh serve   # generate + live preview
uv run ./generate.sh build   # generate + build static site
```

## Zensical Configuration

`zensical.toml` configures:

- Site metadata: name "Playground Docs", description, repo URL
- Navigation: explicit nav tree matching content structure
- Theme: Material-style with light/dark toggle
- Search: built-in full-text search
- Markdown extensions: tables, admonitions, code highlighting with line numbers, tabbed content blocks
- Content directory: `docs/content/`

## API Reference Auto-Generation

`docs/generate.sh` orchestrates spec extraction before Zensical build:

1. Scans `apps/api-lab/openapi/openapi.yaml` for the OpenAPI spec, converts to markdown tables (endpoints, parameters, request/response schemas)
2. Scans `apps/api-lab/openapi/proto/` for `.proto` files, extracts service/method/message definitions via text parsing
3. Exports GraphQL SDL from Strawberry schema (`apps/api-lab/graphql-gateway/src/schema.py`) by running `python -c "from schema import graphql_schema; print(graphql_schema.as_str())"`, then parses the SDL into markdown
4. Writes generated markdown to `docs/content/apps/api-lab/api-reference/`
5. Runs `zensical build` or `zensical serve` depending on argument

Missing specs are skipped with a warning printed to stderr.

`docs/generate_api_docs.py` is a standalone Python script. Expected output format for each API type:

**OpenAPI**: H2 per path, H3 per method, table of parameters (name, type, required, description), request body schema, response schemas with status codes.

**Protobuf**: H2 per service, H3 per RPC method (input/output types), H2 per message with field table (name, type, number, description from comments).

**GraphQL**: H2 per type category (queries, mutations, types), field tables with types and descriptions.

## Diagram Generation

Architecture and flow diagrams are authored as Mermaid source files (`.mmd`) in `docs/diagrams/` and rendered to SVG offline via `mermaid-cli` (`mmdc`). SVGs are placed in `docs/content/assets/diagrams/` and referenced in markdown as standard images, enabling browser zoom.

`docs/generate_diagrams.sh` iterates over all `.mmd` files in `docs/diagrams/`, runs `mmdc -i <file>.mmd -o <file>.svg` for each, and writes SVGs to `docs/content/assets/diagrams/`.

Markdown pages reference diagrams as images:
```markdown
![API-Lab Architecture](../assets/diagrams/api-lab-architecture.svg)
```

This approach avoids client-side JavaScript rendering, produces crisp vector graphics, and allows users to open/zoom SVGs directly in the browser.

`mmdc` (mermaid-cli) is an npm package. It is installed and run via `npx` inside `generate_diagrams.sh` — no global install required. The Nix dev shell already provides Node.js.

`generate.sh` calls `generate_diagrams.sh` before `generate_api_docs.py` so diagrams are ready before the site builds.

Initial diagrams:
- `api-lab-architecture.mmd`: service interaction map (REST, gRPC, GraphQL gateway, database)
- `demo-app-architecture.mmd`: service interaction map (greeting, infra-check, traffic-generator)
- `release-flow.mmd`: dev → test → prod promotion workflow
- `ci-pipeline.mmd`: GitHub Actions workflow stages

## Content Strategy

### Home page
Brief intro: homelab playground monorepo for distributed systems experiments across Python, Go, Rust, TypeScript. Quick links to each section.

### Getting Started
Zero to running tests: Nix shell entry, Bazel build/test commands, repo layout orientation. Single page.

### Common Section
Extracted from existing runbooks and expanded with context (why, not just how), prerequisites, and expected outputs. Templates doc restructured from single long README.

### App Sections
Each app gets:
- Index: purpose, architecture diagram (SVG from mermaid), service interaction map, tech stack
- Per-service pages: purpose, how it works, config, how to run/test, design decisions
- Operations: app-specific deployment, monitoring (referencing `monitoring/` configs), system tests, deploy manifest overview (Kustomize overlays, rollout strategies)
- API reference (where applicable): auto-generated

### Content Depth
- Implemented services (python-rest-api, python-grpc-api, graphql-gateway, database, demo-app services): full documentation from source code reading
- Stub services (go-api, ts-api, rust-traffic-generator): lightweight page with purpose, suggested tech stack, status badge/admonition marking it as "planned", implementation getting-started

### Troubleshooting
Common issues: Bazel cache, Nix shell, test failures, Docker/container gotchas.

## Root README Update

Slim down `README.md` to a brief project intro with a prominent link to the docs site. Include instructions:
```bash
cd docs && uv sync && uv run ./generate.sh serve
```

## Constraints

- Local-only deployment (no GitHub Pages, no CI for docs)
- No Bazel coupling
- No heavy third-party doc generators
- Extensible: new apps just add a folder
- Generated API reference files are gitignored, not committed
