#!/bin/bash
set -euo pipefail

TARGET_PKG="$1"
SIMPLE_NAME="$2"

cd "$BUILD_WORKSPACE_DIRECTORY/$TARGET_PKG"

if [ ! -f Dockerfile ]; then
  echo "Error: Dockerfile not found in $TARGET_PKG"
  exit 1
fi

echo "Building Docker image: ${SIMPLE_NAME}:latest"
docker build -t "${SIMPLE_NAME}:latest" .

echo "Image built successfully: ${SIMPLE_NAME}:latest"
docker images "${SIMPLE_NAME}:latest"
