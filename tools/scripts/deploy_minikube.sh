#!/bin/bash
set -euo pipefail

TARGET_PKG="$1"
IMAGE_REPO="$2"
SIMPLE_NAME="$3"

# Switch to minikube context
echo "Switching to minikube context..."
kubectl config use-context minikube

echo "Loading image to minikube..."
# Assuming image is built locally as simple_name:latest by a previous step or simply tagged
# Note: The original script loaded {simple_name}:latest. 
# We need to ensure the image exists. 
minikube image load "${SIMPLE_NAME}:latest"

echo "Deploying to minikube..."
DEPLOY_DIR="$BUILD_WORKSPACE_DIRECTORY/$TARGET_PKG/deploy"

# Extract parent directory name (e.g., demo-concept from apps/demo-concept/py-app)
# TARGET_PKG is like apps/demo-concept/py-app
PARENT_DIR=$(echo "$TARGET_PKG" | cut -d'/' -f2)
NAMESPACE="playground-dev-$PARENT_DIR"

# Ensure namespace exists
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

if [ -d "$DEPLOY_DIR/dev" ]; then
  kubectl apply -k "$DEPLOY_DIR/dev" -n "$NAMESPACE"
elif [ -d "$DEPLOY_DIR/base" ]; then
  kubectl apply -k "$DEPLOY_DIR/base" -n "$NAMESPACE"
else
  echo "Error: No deploy directory found at $DEPLOY_DIR"
  exit 1
fi

echo "Deployment complete to namespace: $NAMESPACE"
