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

### Identity and Authentication (Keycloak)

Keycloak serves as the identity provider for all services. It issues JWTs that services validate on every request.

**JWT validation flow:**

1. Client authenticates with Keycloak and receives an access token (JWT)
2. Client sends the JWT in the `Authorization: Bearer <token>` header
3. The receiving service validates the JWT signature against Keycloak's JWKS endpoint
4. Claims (roles, scopes) are extracted and used for authorization decisions

### Infrastructure

Local development uses Docker Compose for backing services (PostgreSQL, Redis, Kafka, MongoDB, Jaeger, Keycloak). The same services are available on Minikube via Kubernetes manifests.

## Security

- OCI images use distroless base images
- Containers run as non-root with read-only filesystems
- Network policies restrict inter-service communication
- Nightly Trivy scans check for vulnerabilities
- Pre-commit hooks detect secrets and private keys
- Rate limiting at the API gateway and individual service level
- JWT-based authentication via Keycloak for all API endpoints
- Role-based access control (RBAC) enforced per endpoint
- Security headers (HSTS, CSP, X-Content-Type-Options, X-Frame-Options) on all HTTP responses
- Bandit static analysis and pip-audit dependency scanning in CI
