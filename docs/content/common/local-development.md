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
| Keycloak | 8080 | Identity provider (JWT issuer) |

**Note:** If you have an SSH tunnel forwarding port 6379 (e.g., to a remote Redis), stop it before starting Docker Compose or the Redis container will fail to bind.

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

## API Lab Development Scripts

Start all api-lab services and infrastructure in one command:

```bash
cd apps/api-lab
./dev-start.sh
```

Stop everything:

```bash
cd apps/api-lab
./dev-stop.sh
```

Configure the Keycloak realm (run once after first start, or after resetting Keycloak data):

```bash
cd apps/api-lab
./setup-realm.sh
```

## System Tests (API Lab)

System tests require infrastructure (including Keycloak) and all services running:

```bash
cd apps/api-lab
./system-tests/run.sh
```

This starts PostgreSQL, Redis, and Keycloak, runs migrations, configures the Keycloak realm, starts the REST API, gRPC API, and GraphQL gateway, then runs the pytest suite.

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

Hooks include: Ruff (Python), gofmt/golangci-lint (Go), rustfmt/clippy (Rust), Prettier (JS/TS), Buildifier (Bazel), Shellcheck (Shell), Yamllint (YAML), mypy (Python types), markdownlint (Markdown).
