# Rust Traffic Generator

!!! info "Planned"
    This service is scaffolded but not yet implemented. Currently only reads target URLs from environment variables.

Load and stress testing tool for the library API, targeting all three language implementations.

## Overview

| Attribute | Value |
|-----------|-------|
| Language | Rust |
| Source | `apps/api-lab/rust-traffic-generator/` |

## Current State

Minimal scaffolding that accepts target URLs via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PYTHON_API_URL` | `http://localhost:8080` | Python API target |
| `GO_API_URL` | `http://localhost:8081` | Go API target |
| `TS_API_URL` | `http://localhost:8082` | TypeScript API target |

## Planned Workflow

1. List books (`GET /api/v1/books`)
2. Create a book with random data
3. Reserve the book
4. Return the reservation
5. Check inventory
6. Delete the book

## Suggested Implementation

| Component | Crate |
|-----------|-------|
| Async runtime | `tokio` |
| HTTP client | `reqwest` with connection pooling |
| Serialization | `serde` + `serde_json` |
| Random data | `rand` |
| Metrics | `prometheus` crate + `/metrics` endpoint |
| Tracing | `opentelemetry` + `tracing` |

Key features to implement: configurable concurrency, token bucket rate limiting, per-API request metrics (counters, histograms).
