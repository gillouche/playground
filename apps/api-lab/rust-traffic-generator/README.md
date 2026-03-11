# Rust Traffic Generator

Skeleton Rust traffic generator that sends requests to all three API implementations.

## Suggested Crates

| Feature       | Crate                                  |
| ------------- | -------------------------------------- |
| HTTP Client   | `reqwest`                              |
| Async Runtime | `tokio`                                |
| Serialization | `serde` + `serde_json`                 |
| Random Data   | `rand` + `uuid`                        |
| OpenTelemetry | `opentelemetry` + `opentelemetry-otlp` |
| Prometheus    | `prometheus`                           |
| Logging       | `tracing` + `tracing-subscriber`       |
| Rate Limiting | `governor`                             |

## Implementation Guide

1. Create a reqwest HTTP client with connection pooling
2. Implement book lifecycle: list -> create -> reserve -> return -> delete
3. Generate random book data (ISBNs, titles, authors)
4. Add configurable concurrency with tokio tasks
5. Add rate limiting between requests
6. Wire up OpenTelemetry tracing for HTTP calls
7. Add Prometheus metrics (request counts, latency)
8. Target all three APIs (Python, Go, TypeScript)
