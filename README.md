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
