# Service Templates

This directory contains templates for creating new services in the monorepo.

## Python Service

To create a new Python service:

1. Copy the template:

   ```bash
   cp -r docs/templates/python-service apps/<app-name>/<service-name>
   ```

2. Replace placeholders in all files:
   - `{{SERVICE_NAME}}` - Service name (e.g., `my-service`)
   - `{{SERVICE_NAME_UNDERSCORE}}` - Service name with underscores (e.g., `my_service`)
   - `{{SERVICE_DESCRIPTION}}` - Service description
   - `{{APP_NAME}}` - Parent app name (e.g., `demo-app`)

3. Rename `BUILD.bazel.template` to `BUILD.bazel`

4. Generate lockfiles:

   ```bash
   cd apps/<app-name>/<service-name>
   nix develop ./nix#python
   uv pip compile requirements.in -o requirements_lock.txt
   uv pip compile requirements_dev.in -o requirements_dev_lock.txt
   ```

5. Add pip.parse entries to `MODULE.bazel`:

   ```starlark
   pip.parse(
       hub_name = "pip_<service_name>",
       python_version = "3.12",
       requirements_lock = "//apps/<app-name>/<service-name>:requirements_lock.txt",
       download_only = True,
   )
   use_repo(pip, "pip_<service_name>", "pip_<service_name>_dev")
   ```

6. Build and test:

   ```bash
   bazel build //apps/<app-name>/<service-name>:...
   bazel test //apps/<app-name>/<service-name>:..._unit_test
   ```

## Go Service

To create a new Go service:

1. Copy the template:

   ```bash
   cp -r docs/templates/go-service apps/<app-name>/<service-name>
   ```

2. Replace placeholders:
   - `{{SERVICE_NAME}}` - Service name
   - `{{APP_NAME}}` - Parent app name

3. Rename template files:

   ```bash
   mv BUILD.bazel.template BUILD.bazel
   mv go.mod.template go.mod
   ```

4. Initialize dependencies:

   ```bash
   cd apps/<app-name>/<service-name>
   nix develop ./nix#go
   go mod tidy
   ```

5. Add go_deps to `MODULE.bazel` (if using external dependencies):

   ```starlark
   go_deps = use_extension("@gazelle//:extensions.bzl", "go_deps")
   go_deps.from_file(go_mod = "//apps/<app-name>/<service-name>:go.mod")
   use_repo(go_deps, ...)
   ```

6. Build and test:

   ```bash
   bazel build //apps/<app-name>/<service-name>:...
   bazel test //apps/<app-name>/<service-name>:..._unit_test
   ```

## Rust Service

To create a new Rust service:

1. Copy the template:

   ```bash
   cp -r docs/templates/rust-service apps/<app-name>/<service-name>
   ```

2. Replace placeholders:
   - `{{SERVICE_NAME}}` - Service name
   - `{{APP_NAME}}` - Parent app name

3. Rename template files:

   ```bash
   mv BUILD.bazel.template BUILD.bazel
   mv Cargo.toml.template Cargo.toml
   ```

4. Initialize dependencies:

   ```bash
   cd apps/<app-name>/<service-name>
   nix develop ./nix#rust
   cargo generate-lockfile
   ```

5. Add crate_universe to `MODULE.bazel`:

   ```starlark
   crate = use_extension("@rules_rust//crate_universe:extension.bzl", "crate")
   crate.from_cargo(
       name = "crates",
       cargo_lockfile = "//apps/<app-name>/<service-name>:Cargo.lock",
       manifests = ["//apps/<app-name>/<service-name>:Cargo.toml"],
   )
   use_repo(crate, "crates")
   ```

6. Build and test:

   ```bash
   bazel build //apps/<app-name>/<service-name>:...
   bazel test //apps/<app-name>/<service-name>:..._unit_test
   ```

## TypeScript Service

To create a new TypeScript service:

1. Copy the template:

   ```bash
   cp -r docs/templates/typescript-service apps/<app-name>/<service-name>
   ```

2. Replace placeholders:
   - `{{SERVICE_NAME}}` - Service name
   - `{{SERVICE_DESCRIPTION}}` - Service description
   - `{{APP_NAME}}` - Parent app name

3. Rename template files:

   ```bash
   mv BUILD.bazel.template BUILD.bazel
   mv package.json.template package.json
   ```

4. Initialize dependencies:

   ```bash
   cd apps/<app-name>/<service-name>
   nix develop ./nix#node
   pnpm install
   ```

5. Add npm_translate_lock to `MODULE.bazel`:

   ```starlark
   npm = use_extension("@aspect_rules_js//npm:extensions.bzl", "npm")
   npm.npm_translate_lock(
       name = "npm_<service_name>",
       pnpm_lock = "//apps/<app-name>/<service-name>:pnpm-lock.yaml",
   )
   use_repo(npm, "npm_<service_name>")
   ```

6. Build and test:

   ```bash
   bazel build //apps/<app-name>/<service-name>:...
   bazel test //apps/<app-name>/<service-name>:..._unit_test
   ```

## Generated Targets

All `*_application` macros generate these targets:

| Target | Description |
|--------|-------------|
| `{name}_lib` | Library with source code |
| `{name}` | Executable binary |
| `{name}_unit_test` | Unit tests (tag: unit) |
| `{name}_integration_test` | Integration tests (tag: integration) |
| `{name}_lint` | Linting (Python only, tag: lint) |
| `{name}_image` | OCI container image |
| `{name}_push` | Push image to Nexus |
| `{name}_load` | Load image to local Docker |

## Running Tests

```bash
# All tests
bazel test //apps/...

# Only unit tests
bazel test //apps/... --test_tag_filters=unit

# Only integration tests
bazel test //apps/... --test_tag_filters=integration

# Only lint (Python)
bazel test //apps/... --test_tag_filters=lint
```

## Cross-Compilation

Build for ARM64 (Raspberry Pi):

```bash
bazel build --config=arm64 //apps/<app-name>/<service-name>:..._image
```

Build for AMD64 (x86_64):

```bash
bazel build --config=amd64 //apps/<app-name>/<service-name>:..._image
```
