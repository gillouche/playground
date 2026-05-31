# Traffic Generator

An async HTTP load generator that sends continuous requests to the greeting service.

## Overview

| Attribute | Value |
|-----------|-------|
| Framework | httpx (async) |
| Source | `apps/demo-app/traffic-generator-service/` |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TARGET_URL` | `http://greeting-service:8080` | Target service URL |
| `CONCURRENCY` | `10` | Number of concurrent workers |
| `ENABLE_TRACING` | `true` | Enable OpenTelemetry tracing |

## Behavior

1. Waits for the target service to become healthy (polls `/healthz`)
2. Spawns configured number of async workers
3. Each worker sends continuous HTTP requests with 10ms sleep between requests
4. Request timeout: 5 seconds
5. Graceful shutdown on SIGTERM/SIGINT

OpenTelemetry httpx instrumentation propagates trace context to the greeting service, enabling end-to-end trace visibility in Jaeger.

## Running

```bash
bazel run //apps/demo-app/traffic-generator-service:traffic-generator-service
```

Requires the greeting service to be running at the configured `TARGET_URL`.
