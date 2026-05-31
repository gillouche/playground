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

### Generated Models from OpenAPI

Services that use OpenAPI specs generate Python models via a Bazel genrule:

```python
genrule(
    name = "generate_models",
    srcs = ["openapi.yaml"],
    outs = ["src/generated/models.py"],
    cmd = "$(location //tools:openapi_codegen) --input $< --output $@",
)
```

Generated files are excluded from linting and formatting hooks.

### Dependency Lockfiles

Python dependencies use `pip-compile` with hash checking to produce deterministic lockfiles:

```bash
pip-compile --generate-hashes requirements.in -o requirements.txt
```

Bazel consumes these lockfiles for hermetic builds.

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
