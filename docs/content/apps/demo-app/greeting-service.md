# Greeting Service

A simple HTTP service that returns personalized greetings. Serves as the baseline example for the monorepo's service patterns.

## Overview

| Attribute | Value |
|-----------|-------|
| Framework | FastAPI |
| Port | 8080 |
| Source | `apps/demo-app/greeting-service/` |

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Returns greeting for the given `name` query parameter |
| GET | `/healthz` | Liveness probe |
| GET | `/ready` | Readiness probe |
| GET | `/info` | Service metadata |
| GET | `/metrics` | Prometheus metrics |

The greeting response includes the current environment name: "Hello, {name}! Welcome to the Playground ({environment})."

User input is HTML-escaped to prevent XSS.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Log level |
| `ENABLE_TRACING` | `false` | Enable OpenTelemetry |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | - | OTLP collector endpoint |
| `NAMESPACE` | - | Kubernetes namespace |
| `ENVIRONMENT` | - | Environment name (shown in greeting) |
| `APP_VERSION` | - | Application version |

## Deployment

Canary deployment via Argo Rollouts:

- Steps: 20% -> 40% -> 60% -> 80%
- Analysis: success-rate and error-rate templates
- Pauses: 30s after first step, 10s between subsequent steps

Resource limits: 256Mi memory, 100m CPU (request) / 512Mi memory, 200m CPU (limit).

Targets Raspberry Pi nodes (`topology.kubernetes.io/node-group: rpi`).

## Running

```bash
bazel run //apps/demo-app/greeting-service:greeting-service
```

## Testing

```bash
bazel test //apps/demo-app/greeting-service:greeting-service_unit_test
```
