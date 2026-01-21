FROM ghcr.io/actions/actions-runner:latest

# Switch to root to install packages
USER root

# Install build tools required by Bazel
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Bazelisk (skip version check during build to avoid QEMU issues)
RUN curl -L https://github.com/bazelbuild/bazelisk/releases/download/v1.28.1/bazelisk-linux-amd64 \
    -o /usr/local/bin/bazelisk \
    && chmod +x /usr/local/bin/bazelisk

# Switch back to runner user
USER runner
