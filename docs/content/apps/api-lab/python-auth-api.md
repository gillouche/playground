# Python Auth API

Authentication and user management service, built with FastAPI and backed by Keycloak.

## Overview

| Attribute | Value |
|-----------|-------|
| Framework | FastAPI |
| Port | 8084 |
| Path prefix | `/api/v1/auth` |
| Source | `apps/api-lab/python-auth-api/` |

## Endpoints

### Authentication (Public)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Register a new user |
| POST | `/api/v1/auth/login` | Authenticate and receive tokens |
| POST | `/api/v1/auth/refresh` | Refresh an access token |
| POST | `/api/v1/auth/logout` | Invalidate a refresh token |

### Profile (Authenticated)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/auth/me` | Get current user profile |
| PATCH | `/api/v1/auth/me` | Update profile (email, name) |
| POST | `/api/v1/auth/me/change-password` | Change password |

### User Management (Admin only)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/users` | Create a user |
| GET | `/api/v1/auth/users` | List users (paginated) |
| GET | `/api/v1/auth/users/{user_id}` | Get a user by ID |
| PATCH | `/api/v1/auth/users/{user_id}/roles` | Add or remove roles |
| DELETE | `/api/v1/auth/users/{user_id}` | Deactivate a user |

### Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/healthz` | Public | Liveness probe |
| GET | `/ready` | Public | Readiness probe (checks Keycloak connectivity) |
| GET | `/info` | Admin only | Service metadata |

## Keycloak Integration

The auth API delegates all identity operations to Keycloak via its Admin REST API and token endpoint:

- **User creation** creates a Keycloak user and assigns the default `user` role
- **Login** performs a `password` grant against the Keycloak token endpoint
- **Token refresh** performs a `refresh_token` grant
- **Logout** revokes the refresh token at the Keycloak logout endpoint
- **Admin operations** use a service account (`api-lab-auth-service` client) with `client_credentials` grant

The admin token is cached and automatically refreshed 30 seconds before expiry.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `KEYCLOAK_SERVER_URL` | `http://localhost:8180` | Keycloak server base URL |
| `KEYCLOAK_REALM` | `api-lab` | Keycloak realm name |
| `KEYCLOAK_CLIENT_ID` | `api-lab` | Client ID for user authentication (password grant) |
| `KEYCLOAK_CLIENT_SECRET` | `api-lab-secret` | Client secret for user authentication |
| `KEYCLOAK_AUTH_SERVICE_CLIENT_ID` | `api-lab-auth-service` | Service account client ID (admin operations) |
| `KEYCLOAK_AUTH_SERVICE_CLIENT_SECRET` | `api-lab-auth-service-secret` | Service account client secret |
| `KEYCLOAK_TIMEOUT` | `30` | HTTP timeout for Keycloak requests (seconds) |
| `REDIS_HOST` | `localhost` | Redis host (for rate limiting) |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_PASSWORD` | - | Redis password |
| `LOG_LEVEL` | `INFO` | Log level |
| `ENABLE_TRACING` | `false` | Enable OpenTelemetry tracing |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | - | OTLP collector endpoint |

## Security

- **Rate limiting** on login and register endpoints (auth tier: 10 requests per 60 seconds)
- **Input validation** on registration: username (3-100 chars, alphanumeric), email (5-255 chars), password (8-128 chars)
- **Security headers** on all responses (same as REST API)
- **Body size limit** (1 MB)
- **CORS** restricted to explicit origins
- **Security event logging** for login success/failure, registration, and rate limit hits

## Observability

**Metrics** (Prometheus, via `/metrics`):

- `login_attempts_total{status}` - Counter (success/failure)
- `registrations_total` - Counter
- `auth_failures_total{reason}` - Counter
- `authz_failures_total{endpoint,role}` - Counter
- `rate_limit_rejections_total{endpoint,tier}` - Counter

## Running

```bash
bazel run //apps/api-lab/python-auth-api:python-auth-api
```

## Testing

```bash
bazel test //apps/api-lab/python-auth-api:python-auth-api_unit_test
```
