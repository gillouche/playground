# Playground Monorepo

A modern polyglot monorepo supporting Python, Rust, Go, and TypeScript with Bazel build orchestration, Nix development environments, and GitOps deployment.

## Quick Start

### Prerequisites
- [Nix](https://nixos.org/download.html) with flakes enabled
- [direnv](https://direnv.net/) (optional but recommended)
- [Bazelisk](https://github.com/bazelbuild/bazelisk)

### Local Development (Minikube)

```bash
# Navigate to project
cd apps/demo-concept/py-app

# Run linting
uv run ruff check .

# Run tests
uv run pytest

# Build Docker image (for minikube)
docker build -t py-app:latest .

# Deploy to minikube
cd ../../..
bazelisk run //apps/demo-concept/py-app:deploy_dev
```

**Note:** The `deploy_dev` target automatically switches to minikube context, loads the image, and deploys to the `playground-demo-concept-dev` namespace.

### Building with Bazel

```bash
# Build everything
bazelisk build //...

# Build specific app
bazelisk build //apps/demo-concept/py-app:image

# Query all lint targets
bazelisk query 'attr(tags, lint, //...)'

# Query all test targets
bazelisk query 'attr(tags, test, //...)'

# Query all OCI push targets
bazelisk query 'kind(oci_push, //...)'
```

### CI/CD Commands

The CI pipeline automatically runs:
```bash
# Build all targets
bazelisk build //...

# Run all linting
bazelisk query 'attr(tags, lint, //...)' | xargs -r -n 1 bazelisk run

# Run all tests
bazelisk query 'attr(tags, test, //...)' | xargs -r -n 1 bazelisk run

# Push all container images (main branch only)
bazelisk query 'kind(oci_push, //...)' | xargs -r -n 1 bazelisk run
```

## Adding a New Application

1. **Create directory structure:**
   ```bash
   mkdir -p apps/my-app/{src,tests,deploy}
   ```

2. **Add BUILD.bazel:**
   ```starlark
   load("//:defs.bzl", "application")
   
   application(
       name = "my-app",
       language = "python",  # or "rust", "go", "typescript"
       srcs = glob(["src/**/*.py"]),
       tests = glob(["tests/test_*.py"]),
       image_repository = "nexus.home-cluster:8081/repository/docker-hosted/playground/my-app",
   )
   ```

3. **Add Kubernetes manifests:**
   ```bash
   # Create deploy/deployment.yaml with your K8s resources
   ```

4. **Done!** CI automatically builds/tests/pushes, ArgoCD automatically deploys.

## Supported Languages

### Python
- **Tools:** UV for dependency management, Ruff for linting, pytest for testing
- **Nix Environment:** `python313` + `uv`
- **Default Commands:**
  - Lint: `uv run ruff check .`
  - Test: `uv run pytest`
  - Build: `uv sync`

### Rust (Coming Soon)
- **Tools:** Cargo for build/test, Clippy for linting
- **Default Commands:**
  - Lint: `cargo clippy`
  - Test: `cargo test`
  - Build: `cargo build --release`

### Go (Coming Soon)
- **Tools:** Go toolchain, golangci-lint
- **Default Commands:**
  - Lint: `golangci-lint run`
  - Test: `go test ./...`
  - Build: `go build -o bin/app`

### TypeScript (Coming Soon)
- **Tools:** npm/pnpm, ESLint
- **Default Commands:**
  - Lint: `npm run lint`
  - Test: `npm test`
  - Build: `npm run build`

## Architecture

- **Build System:** Bazel 8.0 for reproducible builds
- **Development Environments:** Nix flakes per-project
- **Dependency Management:** Language-native tools (UV, Cargo, Go modules, npm)
- **Container Images:** rules_oci for multi-arch (amd64 + arm64/v8)
- **Deployment:** ArgoCD ApplicationSet for GitOps
- **CI/CD:** GitHub Actions with self-hosted runners

## Project Structure

```
playground/
├── apps/                    # Application code
│   └── demo-concept/
│       └── py-app/
│           ├── src/         # Source code
│           ├── tests/       # Tests
│           ├── deploy/      # K8s manifests
│           ├── BUILD.bazel  # Bazel build definition
│           ├── flake.nix    # Nix development environment
│           └── pyproject.toml  # Python dependencies
├── defs.bzl                 # Generic application macro
├── MODULE.bazel             # Bazel dependencies
├── .bazelversion            # Bazel version (8.0.0)
└── .github/workflows/       # CI/CD pipelines
```

## Troubleshooting

### `bazelisk test //...` finds no tests
This is expected. Lint and test targets are `sh_binary` (not test rules) because they need access to UV/Nix tools. Use the query-based approach shown above.

### Local `bazelisk run` fails with "command not found"
Bazel runs in a sandbox without your Nix environment. For local development, run commands directly (`uv run ruff`, `uv run pytest`). The Bazel targets are designed for CI execution.

### Tests fail with import errors
Ensure you're in the project directory and the Nix environment is loaded (`direnv allow` or `nix develop`).

## License

MIT
