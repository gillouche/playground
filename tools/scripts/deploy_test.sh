#!/bin/bash
set -euo pipefail

# Wrapper for deploy_test
# Chains promote_test and release_test

echo "Promoting to Test..."
# Forward all arguments (like --concept, --app, --tag)
bazelisk run //tools:promote_test -- "$@"

echo "Creating Release Snapshot..."
bazelisk run //tools:release_test -- "$@"
