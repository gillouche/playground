#!/bin/bash
set -euo pipefail

IMAGE_TARGET="$1"
DEPLOY_TARGET="$2"
PACKAGE="$3"

cd "$BUILD_WORKSPACE_DIRECTORY"

echo "Building OCI image via Bazel (oci_load)..."
# Use the same build process as prod (via oci_load / build_docker)
# This ensures local sandbox matches production exactly
bazelisk run "//$PACKAGE:build_docker"

# The image is now loaded as ${IMAGE_TARGET}:latest in local Docker
echo "Loading image to minikube..."
minikube image load "${IMAGE_TARGET}:latest"

# Update kustomization.yaml to use 'latest' tag for sandbox
KUSTOMIZATION="$PACKAGE/deploy/sandbox/kustomization.yaml"
if [ -f "$KUSTOMIZATION" ]; then
    echo "Ensuring kustomization uses 'latest' tag..."
    # Use perl for portability between Mac and Linux
    perl -pi -e 's/newTag: .*/newTag: latest/' "$KUSTOMIZATION"
else
    echo "Warning: Kustomization file not found at $KUSTOMIZATION"
fi

echo "Deploying to minikube..."
bazelisk run "$DEPLOY_TARGET"
