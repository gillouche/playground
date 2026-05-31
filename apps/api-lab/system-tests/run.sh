#!/usr/bin/env bash
# Run api-lab system tests against local (docker compose) or minikube.
#
# Usage:
#   ./apps/api-lab/system-tests/run.sh [local|minikube] [--keep]
#
# Targets:
#   local     (default) Start infra via docker compose, run services via bazel
#   minikube  Port-forward to services already deployed in minikube
#
# Options:
#   --keep    Keep infrastructure running after tests (local mode only)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/infra/sandbox/localhost/docker-compose.yaml"
KEEP_INFRA=false
TARGET=local

for arg in "$@"; do
    case $arg in
        local|minikube) TARGET="$arg" ;;
        --keep) KEEP_INFRA=true ;;
    esac
done

INFRA_NS="playground-infra-sandbox"
API_LAB_NS="playground-api-lab-sandbox"
PIDS=()

cleanup() {
    echo "Cleaning up..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    for pid in "${PIDS[@]}"; do
        wait "$pid" 2>/dev/null || true
    done
    if [ "$TARGET" = "local" ] && [ "$KEEP_INFRA" = false ]; then
        echo "Stopping infrastructure..."
        $COMPOSE -f "$COMPOSE_FILE" down -v || true
    fi
}
trap cleanup EXIT

export POSTGRES_HOST=localhost
export POSTGRES_DATABASE=api_lab
export POSTGRES_USER=playground
export POSTGRES_PASSWORD=playground
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_PASSWORD=playground
export ENABLE_TRACING=false
export API_BASE_URL=http://localhost:8080
export GRAPHQL_BASE_URL=http://localhost:8083
export GRPC_HOST=localhost:50051

if [ "$TARGET" = "local" ]; then
    if docker compose version &>/dev/null; then
        COMPOSE="docker compose"
    elif command -v docker-compose &>/dev/null; then
        COMPOSE="docker-compose"
    else
        echo "ERROR: Neither 'docker compose' nor 'docker-compose' found"
        exit 1
    fi

    echo "=== Target: local (docker compose + bazel run) ==="

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

    echo "Running database migrations..."
    bazel run //apps/api-lab/database:migrate

    echo "Starting python-rest-api..."
    bazel run //apps/api-lab/python-rest-api &
    PIDS+=($!)

    echo "Starting python-grpc-api..."
    bazel run //apps/api-lab/python-grpc-api &
    PIDS+=($!)

    echo "Starting graphql-gateway..."
    REST_API_URL=http://localhost:8080 bazel run //apps/api-lab/graphql-gateway &
    PIDS+=($!)

elif [ "$TARGET" = "minikube" ]; then
    echo "=== Target: minikube (port-forward to deployed services) ==="

    if ! minikube status --format='{{.Host}}' 2>/dev/null | grep -q Running; then
        echo "ERROR: minikube is not running. Start it with: minikube start"
        exit 1
    fi

    echo "Verifying deployments..."
    for deploy in postgres redis; do
        if ! kubectl get deployment "$deploy" -n "$INFRA_NS" &>/dev/null; then
            echo "ERROR: deployment/$deploy not found in namespace $INFRA_NS"
            echo "Deploy infrastructure first: kubectl apply -k infra/sandbox/minikube/"
            exit 1
        fi
    done
    for deploy in python-api python-grpc-api graphql-gateway; do
        if ! kubectl get deployment "$deploy" -n "$API_LAB_NS" &>/dev/null; then
            echo "ERROR: deployment/$deploy not found in namespace $API_LAB_NS"
            echo "Deploy api-lab first: kubectl apply -k apps/api-lab/deploy/sandbox/"
            exit 1
        fi
    done

    echo "Setting up port-forwards..."

    kubectl port-forward -n "$INFRA_NS" svc/postgres 5432:5432 &>/dev/null &
    PIDS+=($!)

    kubectl port-forward -n "$INFRA_NS" svc/redis 6379:6379 &>/dev/null &
    PIDS+=($!)

    kubectl port-forward -n "$API_LAB_NS" svc/python-api 8080:8080 &>/dev/null &
    PIDS+=($!)

    kubectl port-forward -n "$API_LAB_NS" svc/python-grpc-api 50051:50051 &>/dev/null &
    PIDS+=($!)

    kubectl port-forward -n "$API_LAB_NS" svc/graphql-gateway 8083:8083 &>/dev/null &
    PIDS+=($!)

    echo "Waiting for port-forwards to establish..."
    sleep 3

    echo "Creating api_lab database (if needed)..."
    kubectl exec -n "$INFRA_NS" deployment/postgres -- \
        psql -U playground -c "CREATE DATABASE api_lab" 2>/dev/null || true

    echo "Running database migrations..."
    bazel run //apps/api-lab/database:migrate
fi

echo "Waiting for REST API..."
until curl -sf http://localhost:8080/healthz >/dev/null 2>&1; do sleep 2; done

echo "Waiting for GraphQL gateway..."
until curl -sf http://localhost:8083/healthz >/dev/null 2>&1; do sleep 2; done

echo "Waiting for gRPC (3s after REST)..."
sleep 3

echo "Running system tests..."
bazel test --test_tag_filters=system //apps/api-lab/system-tests:system-tests \
    --test_output=all --test_env=API_BASE_URL --test_env=GRAPHQL_BASE_URL \
    --test_env=GRPC_HOST --test_env=POSTGRES_HOST --test_env=POSTGRES_DATABASE \
    --test_env=POSTGRES_USER --test_env=POSTGRES_PASSWORD \
    --test_env=REDIS_HOST --test_env=REDIS_PORT --test_env=REDIS_PASSWORD
