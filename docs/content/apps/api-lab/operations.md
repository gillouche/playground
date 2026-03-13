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
