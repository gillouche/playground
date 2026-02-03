#!/usr/bin/env bash
set -euo pipefail

REQUIREMENTS_FILE="$1"
OUTPUT_TAR="$2"


# Create temporary directory for installation
mkdir -p tmp/app/site-packages

# Install dependencies
uv pip install -r "$REQUIREMENTS_FILE" \
    --target tmp/app/site-packages \
    --system \
    --python-version 3.12 \
    --python-platform aarch64-unknown-linux-gnu \
    --no-build

# Set deterministic timestamps and ownership for reproducibility
find tmp/app -exec touch -t 197001010000 {} +

# Create the tarball
# We use -C tmp to make paths relative to the root of the tar
tar --owner=0 --group=0 --mode=0755 -cf "$OUTPUT_TAR" -C tmp .

# Cleanup (optional as genrule sandbox handles this, but good practice)
rm -rf tmp
