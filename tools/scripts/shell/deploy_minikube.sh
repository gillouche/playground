#!/usr/bin/env bash

set -euo pipefail

TARGET_PKG="$1"
IMAGE_REPO="$2"
SIMPLE_NAME="$3"

# Switch to minikube context
echo "Switching to minikube context..."
kubectl config use-context minikube

echo "Loading image to minikube..."
minikube image load "${SIMPLE_NAME}:latest"

echo "Deploying to minikube..."
DEPLOY_DIR="$BUILD_WORKSPACE_DIRECTORY/$TARGET_PKG/deploy"

# Extract app name (e.g., demo-app from apps/demo-app/greeting-service)
# TARGET_PKG is like apps/demo-app/greeting-service
APP_NAME=$(echo "$TARGET_PKG" | cut -d'/' -f2)
NAMESPACE="playground-apps-sandbox-$APP_NAME"

# Ensure namespace exists
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

if [ -d "$DEPLOY_DIR/sandbox" ]; then
  kubectl apply -k "$DEPLOY_DIR/sandbox" -n "$NAMESPACE"
elif [ -d "$DEPLOY_DIR/base" ]; then
  kubectl apply -k "$DEPLOY_DIR/base" -n "$NAMESPACE"
else
  echo "Error: No deploy directory found at $DEPLOY_DIR"
  exit 1
fi

kubectl rollout restart deployment -n "$NAMESPACE"

echo "Deployment complete to namespace: $NAMESPACE"
