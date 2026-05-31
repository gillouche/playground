#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/infra/sandbox/localhost/docker-compose.yaml"
PIDS_FILE="$SCRIPT_DIR/.dev-pids"

if docker compose version &>/dev/null; then
    COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE="docker-compose"
else
    echo "ERROR: Neither 'docker compose' nor 'docker-compose' found"
    exit 1
fi

echo "=== Stopping api-lab development stack ==="

echo "[1/2] Stopping background services..."
if [ -f "$PIDS_FILE" ]; then
    while IFS= read -r pid; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo "  Stopping PID $pid..."
            kill "$pid" 2>/dev/null || true
        fi
    done < "$PIDS_FILE"

    while IFS= read -r pid; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            wait "$pid" 2>/dev/null || true
        fi
    done < "$PIDS_FILE"

    rm -f "$PIDS_FILE"
    echo "  Background services stopped."
else
    echo "  No PID file found, skipping background service cleanup."
    echo "  If services are still running, find them with: ps aux | grep 'bazel run.*api-lab'"
fi

echo "[2/2] Stopping docker-compose infrastructure..."
$COMPOSE -f "$COMPOSE_FILE" down -v

echo ""
echo "=========================================="
echo "  api-lab development stack stopped"
echo "=========================================="
