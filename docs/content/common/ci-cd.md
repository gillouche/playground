# CI/CD

## Overview

![CI Pipeline](../assets/diagrams/ci-pipeline.svg)

## GitHub Actions Workflows

### ci.yaml (Main Pipeline)

Triggered on every push and pull request. Runs security checks, builds, tests, and publishes images.

**Jobs:**

1. **security-check** - Gate for artifact access
2. **demo-app** (20 min timeout) - Build and test all demo-app services
3. **api-lab** (20 min timeout) - Build and test all api-lab services, push images to Nexus (main branch only). Includes:
   - Bandit security scanning via `uv tool run bandit`
   - pip-audit dependency vulnerability scanning
   - API coverage enforcement (`--enforce` flag fails the build if coverage is not 100%)
4. **system-test-api-lab** (15 min timeout) - Start infrastructure via Docker Compose (including Keycloak), run database migrations, configure Keycloak realm, start services, execute system tests
5. **finalize** - Push Nix cache (main only), send Discord notifications (checks system-test-api-lab result in addition to build jobs)

Concurrency: `ci-{{ github.ref }}` - new pushes to the same branch cancel in-progress runs.

### release.yaml

Triggered on tag pushes matching `*/*/*` pattern (e.g., `demo-app/greeting-service/v0.0.1`).

Parses the tag to extract app, component, and version. Retags the Docker image from commit SHA to version tag in Nexus.

### sonarqube.yaml

Triggered on push to main only. Uses change detection to identify which services were modified and runs tests with coverage only for those services before submitting results to SonarQube.

### security-scan.yaml

Nightly cron (02:00 UTC). Discovers all OCI image targets, builds them, and runs Trivy vulnerability scanning. Results are aggregated and sent to Discord.

## Runners

All jobs run on self-hosted `playground-runner` pool using custom ARC (Actions Runner Controller) containers.
