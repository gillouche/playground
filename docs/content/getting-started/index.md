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
