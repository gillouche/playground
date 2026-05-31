# Playground

A polyglot monorepo for experimenting with distributed systems in a homelab environment.
This project explores building the same services across multiple languages and protocols,
with production-grade infrastructure including CI/CD, observability, and GitOps deployment.

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
