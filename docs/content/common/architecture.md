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
