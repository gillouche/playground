# API Lab Operations

## Development Scripts

### Starting the Stack

```bash
./apps/api-lab/scripts/dev-start.sh
```

Starts the full development stack in order:

1. PostgreSQL, Redis, Jaeger via Docker Compose
2. Keycloak (with its own PostgreSQL database)
3. Keycloak realm setup (clients, roles, service accounts)
4. Database migrations
5. All four Python services (REST API, gRPC API, GraphQL Gateway, Auth API)
6. Health check verification

After startup, services are available at:

| Service | URL |
|---------|-----|
| REST API | `http://localhost:8080` |
| Auth API | `http://localhost:8084` |
| GraphQL Gateway | `http://localhost:8083` |
| gRPC API | `localhost:50051` |
| Keycloak | `http://localhost:8180` |
| Jaeger UI | `http://localhost:16686` |
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |

### Stopping the Stack

```bash
./apps/api-lab/scripts/dev-stop.sh
```

Stops all running services and tears down Docker Compose infrastructure.

## Keycloak Setup

### Realm Configuration

The `api-lab` realm is configured automatically by `infra/sandbox/localhost/keycloak/setup-realm.sh` during `dev-start.sh`. It creates:

- **Realm:** `api-lab`
- **Clients:**
  - `api-lab` -- user-facing client for password and refresh token grants
  - `api-lab-auth-service` -- service account client for admin operations (user creation, role management)
- **Realm roles:** `admin`, `user`
- **Service account roles:** The `api-lab-auth-service` client receives realm management permissions

### Dev Credentials

| Resource | Username | Password |
|----------|----------|----------|
| Keycloak admin console | `admin` | `admin` |
| PostgreSQL | `playground` | `playground` |
| Redis | - | `playground` |

Client secrets for local development are set in `dev-start.sh` environment variables (`KEYCLOAK_CLIENT_SECRET=dev-secret`, `KEYCLOAK_AUTH_SERVICE_CLIENT_SECRET=dev-auth-secret`).

## System Tests

End-to-end tests that validate all three API protocols (REST, gRPC, GraphQL) and cross-protocol data consistency. The test runner supports two targets: docker compose (local) and minikube.

**Prerequisites:** Keycloak must be running and the realm must be configured before system tests can execute, as all API endpoints require authentication.

### Local (Docker Compose)

```bash
./apps/api-lab/system-tests/run.sh local
```

Starts PostgreSQL and Redis via Docker Compose, runs services via `bazel run`, executes the test suite, and cleans up. Use `--keep` to leave infrastructure running after tests.

### Minikube

```bash
./apps/api-lab/system-tests/run.sh minikube
```

Port-forwards to services already deployed in minikube and runs the same test suite. Requires infrastructure deployed to `playground-infra-sandbox` and api-lab services deployed to `playground-api-lab-sandbox`:

```bash
kubectl apply -k infra/sandbox/minikube/
kubectl apply -k apps/api-lab/deploy/sandbox/
```

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

## Secrets Management

Sensitive configuration (Keycloak client secrets, database passwords, Redis passwords) is managed via **SealedSecrets** for deployed environments.
Credential templates live in each service's deploy directory (e.g., `apps/api-lab/python-rest-api/deploy/templates/credentials.ytt.yaml`)
and sealed versions are stored per environment:

- `apps/api-lab/deploy/dev/` -- dev cluster credentials
- `apps/api-lab/deploy/test/` -- test cluster credentials
- `apps/api-lab/deploy/prod/` -- production cluster credentials

Local development uses plaintext environment variables set by `dev-start.sh`.
