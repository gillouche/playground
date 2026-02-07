# Adding a New Service

## 1. Create Directory
```bash
mkdir -p apps/my-app/new-service
```

## 2. Add Code
*   Add source code `src/main.py` (or main.go, etc.).
*   Add `BUILD.bazel` defining the binary and image.
    *   Use `py_binary` / `go_binary`.
    *   Use `oci_image` from `//tools:python_defs.bzl`.

## 3. Deployment Manifests
*   Create `deploy/templates/rollout.ytt.yaml`.
*   Create `deploy/templates/values.yml`.
*   Use `ytt` templating for things that change per env (replicas, ingress hosts).

## 4. Integrate with Tools
*   Add to `apps/my-app/BUILD.bazel`:
    *   `deploy_targets(...)` macro.
*   Run generation:
    ```bash
    ./tools/scripts/shell/ytt_gen.sh
    ```

## 5. Add to Kustomize
*   Update `apps/my-app/deploy/{dev,test,prod}/kustomization.yaml` to include the new service manifests.
