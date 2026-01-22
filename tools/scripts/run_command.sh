#!/bin/bash
set -euo pipefail

TARGET_PKG="$1"
shift
CMD="$@"

# Navigate to the package directory within the workspace
cd "$BUILD_WORKSPACE_DIRECTORY/$TARGET_PKG"

# Execute the command
exec bash -c "$CMD"
