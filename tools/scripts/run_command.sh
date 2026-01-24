#!/bin/bash
set -euo pipefail

TARGET_PKG="$1"
shift
CMD="$@"

cd "$BUILD_WORKSPACE_DIRECTORY/$TARGET_PKG"

exec bash -c "$CMD"
