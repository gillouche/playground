# Service Templates

Templates for creating new services in the monorepo. Each template provides a standard structure with BUILD.bazel, source code, tests, and deployment manifests.

## Available Templates

=== "Python"

    ```
    apps/<app>/<service>/
      src/
        main.py
      tests/
        unit/
          test_main.py
      BUILD.bazel
      requirements.in
      requirements_lock.txt
    ```

    Setup:
    ```bash
    cp -r docs/templates/python apps/<app>/<new-service>
    cd apps/<app>/<new-service>
    # Update BUILD.bazel name and dependencies
    # Generate lock file:
    uv pip compile requirements.in -o requirements_lock.txt
    ```

=== "Go"

    ```
    apps/<app>/<service>/
      main.go
      go.mod
      go.sum
      BUILD.bazel
    ```

    Setup:
    ```bash
    cp -r docs/templates/go apps/<app>/<new-service>
    cd apps/<app>/<new-service>
    go mod init github.com/gillouche/playground/apps/<app>/<new-service>
    ```

=== "Rust"

    ```
    apps/<app>/<service>/
      src/
        main.rs
      Cargo.toml
      Cargo.lock
      BUILD.bazel
    ```

=== "TypeScript"

    ```
    apps/<app>/<service>/
      src/
        index.ts
      package.json
      pnpm-lock.yaml
      tsconfig.json
      BUILD.bazel
    ```

## After Creating a Service

1. Add the pip hub entry in `MODULE.bazel` (Python only)
2. Add deployment manifests under `apps/<app>/deploy/`
3. Add the service to `tools/deploy/ytt_gen.sh`
4. Update Kustomize overlays for each environment
