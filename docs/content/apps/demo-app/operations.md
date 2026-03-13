# Demo App Operations

## Deployment

All three services deploy via Kustomize with environment-specific overlays at `apps/demo-app/deploy/{dev,test,prod}/`.

### Canary Strategy

Services use Argo Rollouts with canary deployment:

1. Route 20% of traffic to new version, wait 30s, run analysis
2. Increase to 40%, wait 10s
3. Increase to 60%, wait 10s
4. Increase to 80%, wait 10s
5. Full rollout

Analysis templates check success rate and error rate against Prometheus metrics.

### Resources

| Service | Memory (request/limit) | CPU (request/limit) |
|---------|----------------------|---------------------|
| Greeting Service | 256Mi / 512Mi | 100m / 200m |
| Infra Check Service | 256Mi / 512Mi | 100m / 200m |
| Traffic Generator | 128Mi / 256Mi | 50m / 100m |

### Network Policies

- Ingress: allowed from ingress controller
- Egress (infra-check only): allowed to PostgreSQL, Redis, Kafka, MongoDB

### Autoscaling

KEDA ScaledObjects configured for HTTP-based autoscaling.

## Monitoring

### Grafana Dashboard

A Grafana dashboard is deployed as a ConfigMap at `apps/demo-app/deploy/{env}/monitoring-grafana-dashboard.yaml`.

### ServiceMonitors

Each service has a Prometheus ServiceMonitor that scrapes the `/metrics` endpoint.

### Tracing

OpenTelemetry traces are exported to Jaeger via OTLP. The traffic generator propagates trace context to the greeting service, enabling end-to-end request tracing.
