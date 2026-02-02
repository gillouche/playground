#!/usr/bin/env bash

set -euo pipefail

APP_NAME="$1"
APP_DIR="$BUILD_WORKSPACE_DIRECTORY/apps/$APP_NAME"
SANDBOX_DIR="$APP_DIR/deploy/sandbox"
NAMESPACE="playground-apps-sandbox-$APP_NAME"

echo "Switching to minikube context..."
kubectl config use-context minikube

echo "======================================"
echo "Discovering components in $APP_DIR..."
echo "======================================"

# Find all component directories (those with a BUILD file, excluding deploy/monitoring)
cd "$APP_DIR"
for component in */; do
    component="${component%/}"
    
    # Skip non-component directories
    if [ "$component" = "deploy" ] || [ "$component" = "monitoring" ]; then
        echo "Skipping $component (not a component)"
        continue
    fi
    
    # Check if this is a buildable component (has BUILD or BUILD.bazel file)
    if [ -f "$component/BUILD" ] || [ -f "$component/BUILD.bazel" ]; then
        target="//apps/$APP_NAME/$component"
        
        echo "======================================"
        echo "Building $component..."
        echo "======================================"
        
        # Build and load the Docker image
        bazel run "${target}:build_docker"
        
        echo "Loading $component image to minikube..."
        minikube image load "${component}:latest"
    else
        echo "Skipping $component (no BUILD file)"
    fi
done

echo "======================================"
echo "Creating namespace if needed..."
echo "======================================"
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

echo "======================================"
echo "Deploying all components from $SANDBOX_DIR..."
echo "======================================"
if [ -d "$SANDBOX_DIR" ]; then
  kubectl apply -k "$SANDBOX_DIR" -n "$NAMESPACE"
else
  echo "Error: Sandbox directory not found at $SANDBOX_DIR"
  exit 1
fi

echo "======================================"
echo "Deployment complete to namespace: $NAMESPACE"
echo "======================================"
