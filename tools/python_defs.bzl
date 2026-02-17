"""
Pure Bazel macros for polyglot monorepo applications.

This module provides the python_application macro for building Python services
with hermetic dependencies, OCI image packaging, and deployment targets.

For other languages, use the dedicated macro files:
- Go: //tools:go_defs.bzl (go_application)
- Rust: //tools:rust_defs.bzl (rust_application)
- TypeScript: //tools:ts_defs.bzl (typescript_application)

Key design principles:
- Nix provides toolchains (Python, Go, Rust, Node.js)
- Bazel manages third-party dependencies (pip.parse, go_deps, etc.)
- No shell commands for builds - everything is pure Bazel
"""

load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load", "oci_push")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:defs.bzl", "py_binary", "py_library", "py_test")
load("//tools:transitions.bzl", "transition_rule")

def python_application(
        name,
        srcs,
        deps = [],
        main = None,
        unit_tests = [],
        integration_tests = [],
        test_deps = [],
        data = [],
        env = {},
        base_image = "@python_base_linux_arm64",
        image_repository = "",
        visibility = ["//visibility:public"]):
    """
    Creates a Python application with library, binary, tests, and OCI image targets.

    This macro generates pure Bazel targets without any shell command wrappers.
    Dependencies are managed by rules_python pip.parse, not UV.

    Args:
        name: Application name (e.g., "greeting-service")
        srcs: Source files (glob of .py files)
        deps: Runtime dependencies from pip.parse (e.g., requirement("fastapi"))
        main: Main entrypoint file (default: src/main.py)
        unit_tests: Unit test files
        integration_tests: Integration test files
        test_deps: Additional test dependencies
        data: Data files to include
        env: Environment variables for the binary
        base_image: OCI base image (default: python_base for ARM64)
        image_repository: Nexus repository path (auto-inferred from package path)
        visibility: Bazel visibility

    Generated targets:
        {name}_lib        - py_library with source code
        {name}            - py_binary executable
        {name}_unit_test  - py_test for unit tests
        {name}_integration_test - py_test for integration tests
        {name}_image      - OCI image
        {name}_push       - oci_push to registry
        {name}_load       - oci_load to local Docker
    """

    if not main:
        main = "src/main.py"

    package_path = native.package_name()

    py_library(
        name = name + "_lib",
        srcs = srcs,
        deps = deps,
        imports = ["src"],
        data = data,
        visibility = visibility,
    )

    py_binary(
        name = name,
        srcs = [main],
        main = main,
        deps = [":" + name + "_lib"] + deps,
        data = data,
        env = env,
        visibility = visibility,
    )

    if unit_tests:
        py_test(
            name = name + "_unit_test",
            srcs = ["//tools:pytest_runner.py"] + unit_tests + srcs,
            main = "//tools:pytest_runner.py",
            # Let pytest discover tests in current directory
            args = ["-v", "--import-mode=importlib", "."],
            deps = deps + test_deps,
            # Add "." for current package and "src" for source imports
            imports = [".", "src"],
            size = "small",
            tags = ["unit"],
            visibility = visibility,
        )

    if integration_tests:
        py_test(
            name = name + "_integration_test",
            srcs = ["//tools:pytest_runner.py"] + integration_tests + srcs,
            main = "//tools:pytest_runner.py",
            args = ["-v", "--import-mode=importlib", "."],
            deps = deps + test_deps,
            imports = [".", "src"],
            size = "medium",
            tags = ["integration"],
            visibility = visibility,
        )

    # Note: Lint targets removed - ruff is a native binary that doesn't integrate
    # well with rules_python py_test. Run ruff manually or via pre-commit hooks.

    if package_path.startswith("apps/"):
        if not image_repository:
            repo_suffix = package_path[len("apps/"):]
            image_repository = "nexus.gillouche.homelab/docker-hosted/{}".format(repo_suffix)

        pkg_tar(
            name = name + "_layer",
            srcs = [":" + name],
            package_dir = "/app",
            include_runfiles = True,
            mode = "0755",
        )

        oci_image(
            name = name + "_image",
            base = base_image,
            tars = [":" + name + "_layer"],
            entrypoint = ["/usr/local/bin/python3", "/app/{}".format(name)],
            workdir = "/app",
            env = dict({
                "PYTHONUNBUFFERED": "1",
            }, **env),
            labels = {
                "org.opencontainers.image.source": "https://github.com/gillouche/playground",
                "org.opencontainers.image.title": name,
                "org.opencontainers.image.description": "{} container image".format(name),
            },
            visibility = visibility,
        )

        # The image is wrapped in a transition to force it to ARM64
        # This allows building the image for ARM64 even when the pusher
        # is running on an AMD64 host (fix for Exec format error on jq).
        transition_rule(
            name = name + "_image_arm64",
            actual = ":" + name + "_image",
            platform = "//tools/platforms:linux_arm64",
            visibility = visibility,
        )

        oci_push(
            name = name + "_push",
            image = ":" + name + "_image_arm64",
            repository = image_repository,
            visibility = visibility,
        )

        oci_load(
            name = name + "_load",
            image = ":" + name + "_image",
            repo_tags = ["{}:latest".format(name)],
            visibility = visibility,
        )

def deploy_sandbox_all(name, app, components = []):
    """
    Creates a target to deploy all components of an app to sandbox.

    This is a placeholder that will be implemented when deployment
    tooling is migrated to pure Bazel.

    Args:
        name: Target name
        app: Application name
        components: List of component names (unused, kept for compatibility)
    """
    native.sh_binary(
        name = name,
        srcs = ["//tools/deploy:deploy_sandbox_all.sh"],
        args = [app],
    )
