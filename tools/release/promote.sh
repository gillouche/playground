#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_DIR="${BUILD_WORKSPACE_DIRECTORY:-$(git rev-parse --show-toplevel)}"
exec python "${WORKSPACE_DIR}/tools/release/promote.py" "$@"
