#!/bin/bash
set -euo pipefail

# Wrapper for deploy_prod
# Chains promote_prod and release_prod

echo "Promoting to Prod..."
# Forward all arguments
bazelisk run //tools:promote_prod -- "$@"

echo "Creating Release Snapshot..."
bazelisk run //tools:release_prod -- "$@"
