# Demo App

A set of Python microservices demonstrating basic patterns for building, testing, and deploying services in the Playground monorepo.

## Architecture

![Demo App Architecture](../../assets/diagrams/demo-app-architecture.svg)

## Services

| Service | Description | Port |
|---------|-------------|------|
| [Greeting Service](greeting-service.md) | Returns personalized greetings | 8080 |
| [Infra Check Service](infra-check-service.md) | Tests connectivity to backend infrastructure | 8080 |
| [Traffic Generator](traffic-generator.md) | Sends continuous load to the greeting service | - |

## Tech Stack

All services are built with FastAPI and share common patterns:

- Prometheus metrics via `prometheus-fastapi-instrumentator`
- OpenTelemetry tracing with OTLP exporter to Jaeger
- Structured logging
- Graceful shutdown via signal handlers
- Distroless container images running as non-root
