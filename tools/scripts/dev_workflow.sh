#!/bin/bash
set -euo pipefail

IMAGE_TARGET="$1"
DEPLOY_TARGET="$2"
PACKAGE="$3"

cd "$BUILD_WORKSPACE_DIRECTORY"

echo "Building OCI image..."
# Build using Dockerfile (minikube doesn't support oci tarballs)

# Generate unique tag
TAG="dev-$(date +%s)"
FULL_IMAGE="$IMAGE_TARGET:$TAG"

echo "Building Docker image locally ($FULL_IMAGE)..."
# $PACKAGE/Dockerfile
docker build --no-cache -t "$FULL_IMAGE" "$PACKAGE"

echo "Loading image to minikube..."
minikube image load "$FULL_IMAGE"

# Update kustomization.yaml with new tag
# $PACKAGE/deploy/dev/kustomization.yaml
KUSTOMIZATION="$PACKAGE/deploy/dev/kustomization.yaml"
if [ -f "$KUSTOMIZATION" ]; then
    echo "Updating kustomization tag to $TAG..."
    # Use perl for portability between Mac and Linux
    perl -pi -e "s/newTag: .*/newTag: $TAG/" "$KUSTOMIZATION"
else
    echo "Warning: Kustomization file not found at $KUSTOMIZATION"
fi

echo "Deploying to minikube..."
bazelisk run "$DEPLOY_TARGET"
