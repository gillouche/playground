#!/bin/bash
set -euo pipefail

# Wrapper for deploy_test
# Chains promote_test and release_test

if [ -n "${BUILD_WORKSPACE_DIRECTORY:-}" ]; then
  cd "$BUILD_WORKSPACE_DIRECTORY"
fi

echo "Promoting to Test..."
# Forward all arguments (like --concept, --app, --tag)
bazel run //tools:promote_test -- "$@"

echo "Creating Release Snapshot..."
bazel run //tools:release_test -- "$@"
