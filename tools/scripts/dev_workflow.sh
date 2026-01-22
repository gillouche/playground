#!/bin/bash
set -euo pipefail

IMAGE_TARGET="$1"
DEPLOY_TARGET="$2"
PACKAGE="$3"

cd "$BUILD_WORKSPACE_DIRECTORY"

echo "Building OCI image..."
bazelisk build "$IMAGE_TARGET"

echo "Loading image to minikube..."
# Load the OCI tarball directly to minikube
# Note: minikube image load expects a tarball path relative to execution or absolute.
# Bazel build output is in bazel-bin.
minikube image load "bazel-bin/$PACKAGE/image/tarball.tar" --daemon

echo "Deploying to minikube..."
bazelisk run "$DEPLOY_TARGET"
