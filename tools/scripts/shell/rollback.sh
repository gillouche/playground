#!/usr/bin/env bash
set -euo pipefail

# Use BUILD_WORKSPACE_DIRECTORY if set (running via bazel run), otherwise use git root
if [[ -n "${BUILD_WORKSPACE_DIRECTORY:-}" ]]; then
    WORKSPACE_DIR="${BUILD_WORKSPACE_DIRECTORY}"
else
    WORKSPACE_DIR="$(git rev-parse --show-toplevel)"
fi

exec python "${WORKSPACE_DIR}/tools/scripts/python/rollback.py" "$@"
