#!/bin/bash
set -euo pipefail

# Wrapper for deploy_dev
# Chains sync_dev logic with explicit manifest generation

# 1. Sync BOM with Nexus
python3 tools/scripts/sync_dev.py "$@"

# 2. Regenerate Manifests (Explicit step)
echo "Regenerating manifests..."
bazelisk run //tools:gen_manifests
