# Releasing a New Version

## 1. Sync Dev
Get the latest built images from Nexus into the Dev BOM.
```bash
bazel run //tools:sync_dev -- --app demo-app
```
*   Checks Nexus for new tags.
*   Updates `releases/dev/demo-app.yaml`.
*   Regenerates Dev manifests.

## 2. Freeze Candidate
Snapshot the current Dev state into an immutable release version.
```bash
bazel run //tools:freeze -- --app demo-app --version v1.0.1
```
*   Creates `releases/versions/demo-app/v1.0.1.yaml`.
*   This file is the single source of truth for this release.

## 3. Promote to Test
Deploy the frozen version to the Test environment.
```bash
bazel run //tools:promote -- --app demo-app --version v1.0.1 --target test --commit
```
*   Updates `apps/demo-app/deploy/test/kustomization.yaml`.
*   Commits the change.
*   ArgoCD will sync automatically.

## 4. Promote to Prod
Once verified in Test, ship it.
```bash
bazel run //tools:promote -- --app demo-app --version v1.0.1 --target prod --commit
```
