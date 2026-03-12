#!/usr/bin/env bash
# Local convenience script to run api-lab system tests.
# Usage: ./apps/api-lab/system-tests/run.sh [--keep]
#   --keep: keep infrastructure running after tests
#
# On macOS (colima): expects colima to be running
# On CI (Linux): uses docker compose directly

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/infra/sandbox/localhost/docker-compose.yaml"
KEEP_INFRA=false

for arg in "$@"; do
    case $arg in
        --keep) KEEP_INFRA=true ;;
    esac
done

# Detect docker compose command
if docker compose version &>/dev/null; then
    COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE="docker-compose"
else
    echo "ERROR: Neither 'docker compose' nor 'docker-compose' found"
    exit 1
fi

cleanup() {
    echo "Stopping services..."
    kill "$REST_PID" "$GRPC_PID" "$GQL_PID" 2>/dev/null || true
    wait "$REST_PID" "$GRPC_PID" "$GQL_PID" 2>/dev/null || true
    if [ "$KEEP_INFRA" = false ]; then
        echo "Stopping infrastructure..."
        $COMPOSE -f "$COMPOSE_FILE" down -v || true
    fi
}
trap cleanup EXIT

echo "Starting infrastructure..."
$COMPOSE -f "$COMPOSE_FILE" up -d postgres redis

echo "Waiting for Postgres..."
until $COMPOSE -f "$COMPOSE_FILE" exec -T postgres pg_isready -U playground 2>/dev/null; do
    sleep 2
done

echo "Waiting for Redis..."
until $COMPOSE -f "$COMPOSE_FILE" exec -T redis redis-cli -a playground ping 2>/dev/null | grep -q PONG; do
    sleep 2
done

echo "Creating api_lab database..."
$COMPOSE -f "$COMPOSE_FILE" exec -T postgres \
    psql -U playground -c "CREATE DATABASE api_lab" 2>/dev/null || true

export POSTGRES_HOST=localhost
export POSTGRES_DATABASE=api_lab
export POSTGRES_USER=playground
export POSTGRES_PASSWORD=playground
export REDIS_HOST=localhost
export REDIS_PASSWORD=playground
export ENABLE_TRACING=false

echo "Starting python-rest-api..."
bazel run //apps/api-lab/python-rest-api &
REST_PID=$!

echo "Starting python-grpc-api..."
bazel run //apps/api-lab/python-grpc-api &
GRPC_PID=$!

echo "Starting graphql-gateway..."
REST_API_URL=http://localhost:8080 bazel run //apps/api-lab/graphql-gateway &
GQL_PID=$!

echo "Waiting for REST API..."
until curl -sf http://localhost:8080/healthz >/dev/null 2>&1; do sleep 2; done

echo "Waiting for GraphQL gateway..."
until curl -sf http://localhost:8083/healthz >/dev/null 2>&1; do sleep 2; done

echo "Waiting for gRPC (3s after REST)..."
sleep 3

echo "Running system tests..."
export API_BASE_URL=http://localhost:8080
export GRAPHQL_BASE_URL=http://localhost:8083
export GRPC_HOST=localhost:50051

bazel test --test_tag_filters=system //apps/api-lab/system-tests:system-tests \
    --test_output=all --test_env=API_BASE_URL --test_env=GRAPHQL_BASE_URL \
    --test_env=GRPC_HOST --test_env=POSTGRES_HOST --test_env=POSTGRES_DATABASE \
    --test_env=POSTGRES_USER --test_env=POSTGRES_PASSWORD \
    --test_env=REDIS_HOST --test_env=REDIS_PORT --test_env=REDIS_PASSWORD
