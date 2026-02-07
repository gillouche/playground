# Service Templates

This directory contains templates for creating new services in the monorepo.

## Python Service

To create a new Python service:

1. Copy the template:
   ```bash
   cp -r libs/templates/python-service apps/<app-name>/<service-name>
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

   pip.parse(
       hub_name = "pip_<service_name>_dev",
       python_version = "3.12",
       requirements_lock = "//apps/<app-name>/<service-name>:requirements_dev_lock.txt",
       download_only = True,
   )

   use_repo(pip, "pip_<service_name>", "pip_<service_name>_dev")
   ```

6. Build and test:
   ```bash
   bazel build //apps/<app-name>/<service-name>:...
   bazel test //apps/<app-name>/<service-name>:..._unit_test
   ```

## Generated Targets

The `python_application` macro generates these targets:

| Target | Description |
|--------|-------------|
| `{name}_lib` | py_library with source code |
| `{name}` | py_binary executable |
| `{name}_unit_test` | Unit tests (tag: unit) |
| `{name}_integration_test` | Integration tests (tag: integration) |
| `{name}_lint` | Ruff linting (tag: lint) |
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

# Only lint
bazel test //apps/... --test_tag_filters=lint
```
