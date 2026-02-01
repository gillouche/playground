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

# Extract app name and component name (e.g., demo-app, greeting-service from apps/demo-app/greeting-service)
# TARGET_PKG is like apps/demo-app/greeting-service
APP_NAME=$(echo "$TARGET_PKG" | cut -d'/' -f2)
COMPONENT_NAME=$(echo "$TARGET_PKG" | cut -d'/' -f3)
NAMESPACE="playground-apps-sandbox-$APP_NAME"

# Use component-specific sandbox directory
SANDBOX_DIR="$BUILD_WORKSPACE_DIRECTORY/apps/$APP_NAME/deploy/sandbox/$COMPONENT_NAME"

# Ensure namespace exists
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

if [ -d "$SANDBOX_DIR" ]; then
  kubectl apply -k "$SANDBOX_DIR" -n "$NAMESPACE"
else
  echo "Error: Sandbox directory not found at $SANDBOX_DIR"
  echo "Run 'bazelisk run //tools:gen_manifests -- $APP_NAME $COMPONENT_NAME sandbox' first"
  exit 1
fi

kubectl rollout restart deployment "$COMPONENT_NAME" -n "$NAMESPACE" 2>/dev/null || echo "Deployment $COMPONENT_NAME not found, skipping restart"

echo "Deployment complete to namespace: $NAMESPACE"
