# Playground

Monorepo for my distributed systems experiments. Polyglot (Python, Go, Rust), built with Bazel, managed by Nix, deployed via GitOps.

## Structure
*   `apps/` - Source code for apps/components.
*   `libs/` - Shared libraries.
*   `tools/` - Build & Release scripts.
*   `nix/` - Dev/CI environment definition.
*   `releases/` - Release BOMs.
*   `docs/` - Runbooks.

## Quick Start
1.  **Get Tools:**
    ```bash
    use flake ./nix#bazel
    ```

2.  **Build & Test:**
    ```bash
    bazel test //...
    ```

3.  **Run Locally:**
    ```bash
    bazel run //apps/demo-app/greeting-service:main
    ```

## Runbooks 📘
*   [Local Development](docs/runbooks/local-development.md)
*   [Release New Version](docs/runbooks/release-new-version.md)
*   [Rollback Production](docs/runbooks/rollback-production.md)
*   [Add New Service](docs/runbooks/add-new-service.md)
