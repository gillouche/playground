# Releases

![Release Flow](../assets/diagrams/release-flow.svg)

## Concepts

### Bill of Materials (BOM)

Each release is tracked as a YAML file containing exact image references (tag, commit SHA, full registry path, digest).

### Environments

| Environment | Path | Purpose |
|-------------|------|---------|
| dev | `releases/dev/` | Latest builds from CI |
| test | `releases/test/` | Pre-production validation |
| prod | `releases/prod/` | Production |
| sandbox | `releases/sandbox/` | Local testing |

### Version Snapshots

Immutable version records stored in `releases/versions/<app>/v1.0.0.yaml`. Created by the freeze tool from git tags.

## Workflow

### Releasable Components

| App | Component | Notes |
|-----|-----------|-------|
| demo-app | greeting-service, infra-check-service, traffic-generator-service | Go, Python |
| api-lab | python-rest-api, python-grpc-api, graphql-gateway, python-auth-api | Python |

### Release Checklist

Before promoting to test or production:

- All CI checks pass (including system tests)
- Keycloak realm configuration is up to date (`apps/api-lab/keycloak/realm-export.json`)
- BOM files reference correct image digests

### 1. Sync Dev

Pull latest component images from Nexus and update the dev BOM:

```bash
bazel run //tools:sync_dev -- --app demo-app
```

### 2. Freeze a Version

Create an immutable version snapshot from the current git tags:

```bash
bazel run //tools:freeze -- --app demo-app --version v1.0.1
```

### 3. Promote to Test

```bash
bazel run //tools:promote -- --app demo-app --version v1.0.1 --target test --commit
```

### 4. Promote to Production

```bash
bazel run //tools:promote -- --app demo-app --version v1.0.1 --target prod --commit
```

### 5. Rollback

Revert to the previously deployed version:

```bash
bazel run //tools:rollback -- --app demo-app --target prod --commit
```

For manual rollback to a specific version:

```bash
bazel run //tools:promote -- --app demo-app --version v1.0.0 --target prod
```
