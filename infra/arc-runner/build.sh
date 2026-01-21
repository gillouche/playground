#!/usr/bin/env bash

set -euo pipefail

# Check required environment variables
if [ -z "${NEXUS_PUBLISH_USERNAME:-}" ]; then
  echo "ERROR: NEXUS_PUBLISH_USERNAME environment variable is not set"
  exit 1
fi

if [ -z "${NEXUS_PUBLISH_PASSWORD:-}" ]; then
  echo "ERROR: NEXUS_PUBLISH_PASSWORD environment variable is not set"
  exit 1
fi

# Configuration
REGISTRY="nexus.gillouche.homelab"
IMAGE_NAME="${REGISTRY}/docker-hosted/arc-runner"
IMAGE_TAG="latest"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"

echo "Building custom GitHub Actions runner image for linux/amd64..."

# Create buildx builder if it doesn't exist
docker-buildx create --name arc-builder --use 2>/dev/null || docker-buildx use arc-builder

# Build for linux/amd64 (your K3s cluster architecture)
docker-buildx build \
  --platform linux/amd64 \
  --load \
  -t "${FULL_IMAGE}" \
  .

echo "Logging in to Nexus..."

# Check if CA cert exists and configure Docker to use it
CA_CERT="$HOME/.local/share/ansible-home-cluster/pki/root-ca.crt"
DOCKER_CA_PATH="/etc/docker/certs.d/${REGISTRY}/ca.crt"

if [ -f "$CA_CERT" ]; then
  # Check if using Colima
  if command -v colima &> /dev/null && colima status &> /dev/null; then
    echo "Detected Colima VM - installing CA cert in VM..."
    colima ssh -- sudo mkdir -p /etc/docker/certs.d/${REGISTRY}
    cat "$CA_CERT" | colima ssh -- sudo tee /etc/docker/certs.d/${REGISTRY}/ca.crt > /dev/null
    echo "CA certificate installed in Colima VM for ${REGISTRY}"
  elif [ ! -e "$DOCKER_CA_PATH" ]; then
    echo "Installing CA certificate for Docker..."
    sudo mkdir -p /etc/docker/certs.d/${REGISTRY}
    sudo ln -s "$CA_CERT" "$DOCKER_CA_PATH"
    echo "CA certificate installed"
  else
    echo "CA certificate already configured"
  fi
fi

echo "${NEXUS_PUBLISH_PASSWORD}" | docker login ${REGISTRY} \
  --username "${NEXUS_PUBLISH_USERNAME}" \
  --password-stdin

echo "Pushing image to Nexus..."
docker push "${FULL_IMAGE}"

echo "Successfully built and pushed: ${FULL_IMAGE}"
