#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/infra/sandbox/localhost/docker-compose.yaml"
SETUP_REALM="$PROJECT_ROOT/infra/sandbox/localhost/keycloak/setup-realm.sh"

export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DATABASE=api_lab
export POSTGRES_USER=playground
export POSTGRES_PASSWORD=playground
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_PASSWORD=playground
export ENABLE_TRACING=false
export KEYCLOAK_SERVER_URL=http://localhost:8180
export KEYCLOAK_REALM=api-lab
export KEYCLOAK_CLIENT_ID=api-lab
export KEYCLOAK_AUTH_SERVICE_CLIENT_ID=api-lab-auth-service
export KEYCLOAK_CLIENT_SECRET=dev-secret
export KEYCLOAK_AUTH_SERVICE_CLIENT_SECRET=dev-auth-secret
export KC_BOOTSTRAP_ADMIN_USERNAME=admin
export KC_BOOTSTRAP_ADMIN_PASSWORD=admin
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

PIDS_FILE="$SCRIPT_DIR/.dev-pids"

if docker compose version &>/dev/null; then
    COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE="docker-compose"
else
    echo "ERROR: Neither 'docker compose' nor 'docker-compose' found"
    exit 1
fi

echo "=== Starting api-lab development stack ==="

echo "[1/9] Starting infrastructure (postgres, redis, jaeger)..."
$COMPOSE -f "$COMPOSE_FILE" up -d postgres redis jaeger

echo "[2/9] Waiting for Postgres..."
until $COMPOSE -f "$COMPOSE_FILE" exec -T postgres pg_isready -U playground 2>/dev/null; do
    sleep 2
done
echo "  Postgres is ready."

echo "[3/9] Creating databases (if needed)..."
$COMPOSE -f "$COMPOSE_FILE" exec -T postgres \
    psql -U playground -c "CREATE DATABASE api_lab" 2>/dev/null || true
$COMPOSE -f "$COMPOSE_FILE" exec -T postgres \
    psql -U playground -c "CREATE DATABASE keycloak" 2>/dev/null || true

echo "[4/9] Starting Keycloak..."
$COMPOSE -f "$COMPOSE_FILE" up -d keycloak

echo "[5/9] Waiting for Keycloak..."
until curl -sf http://localhost:8180/realms/master > /dev/null 2>&1; do
    sleep 3
done
echo "  Keycloak is ready."

echo "[6/9] Setting up Keycloak realm (service account roles)..."
if [ -x "$SETUP_REALM" ]; then
    bash "$SETUP_REALM"
else
    echo "  WARNING: setup-realm.sh not found or not executable at $SETUP_REALM"
fi

echo "[7/9] Running database migrations..."
(cd "$PROJECT_ROOT" && bazel run //apps/api-lab/database:migrate)

echo "[8/9] Starting Python services..."
PIDS=()

(cd "$PROJECT_ROOT" && bazel run //apps/api-lab/python-rest-api) &
PIDS+=($!)

(cd "$PROJECT_ROOT" && bazel run //apps/api-lab/python-grpc-api) &
PIDS+=($!)

(cd "$PROJECT_ROOT" && REST_API_URL=http://localhost:8080 bazel run //apps/api-lab/graphql-gateway) &
PIDS+=($!)

(cd "$PROJECT_ROOT" && bazel run //apps/api-lab/python-auth-api) &
PIDS+=($!)

printf "%s\n" "${PIDS[@]}" > "$PIDS_FILE"

echo "[9/9] Waiting for health checks..."

echo "  Waiting for REST API (port 8080)..."
until curl -sf http://localhost:8080/healthz > /dev/null 2>&1; do sleep 2; done
echo "  REST API is healthy."

echo "  Waiting for Auth API (port 8084)..."
until curl -sf http://localhost:8084/healthz > /dev/null 2>&1; do sleep 2; done
echo "  Auth API is healthy."

echo "  Waiting for GraphQL Gateway (port 8083)..."
until curl -sf http://localhost:8083/healthz > /dev/null 2>&1; do sleep 2; done
echo "  GraphQL Gateway is healthy."

echo "  Waiting for gRPC API (port 50051, 3s grace)..."
sleep 3
echo "  gRPC API assumed ready."

echo ""
echo "=========================================="
echo "  api-lab development stack is running"
echo "=========================================="
echo ""
echo "  REST API:          http://localhost:8080"
echo "  Auth API:          http://localhost:8084"
echo "  GraphQL Gateway:   http://localhost:8083"
echo "  gRPC API:          localhost:50051"
echo "  Keycloak:          http://localhost:8180"
echo "  Jaeger UI:         http://localhost:16686"
echo "  PostgreSQL:        localhost:5432"
echo "  Redis:             localhost:6379"
echo ""
echo "  Stop with: ./apps/api-lab/scripts/dev-stop.sh"
echo "=========================================="
