#!/bin/bash
set -euo pipefail

# Wrapper for deploy_prod
# Chains promote_prod and release_prod

if [ -n "${BUILD_WORKSPACE_DIRECTORY:-}" ]; then
  cd "$BUILD_WORKSPACE_DIRECTORY"
fi

echo "Promoting to Prod..."
# Forward all arguments
bazelisk run //tools:promote_prod -- "$@"

echo "Creating Release Snapshot..."
bazelisk run //tools:release_prod -- "$@"
