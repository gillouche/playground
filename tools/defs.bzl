"""
Pure Bazel macros for polyglot monorepo applications.

This module provides macros for building Python (and future Go, Rust, TypeScript)
applications with hermetic dependencies, OCI image packaging, and deployment targets.

Key design principles:
- Nix provides toolchains (Python, Go, Rust, Node.js)
- Bazel manages third-party dependencies (pip.parse, go_deps, etc.)
- No shell commands for builds - everything is pure Bazel
"""

load("@rules_python//python:defs.bzl", "py_binary", "py_library", "py_test")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load", "oci_push")

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
        base_image = "@python_base_linux_arm64_v8",
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

    # Infer main module if not provided
    if not main:
        main = "src/main.py"

    # Get package path for repository inference
    package_path = native.package_name()

    # 1. Create py_library for source code
    py_library(
        name = name + "_lib",
        srcs = srcs,
        deps = deps,
        imports = ["src"],
        data = data,
        visibility = visibility,
    )

    # 2. Create py_binary for main entrypoint
    py_binary(
        name = name,
        srcs = [main],
        main = main,
        deps = [":" + name + "_lib"] + deps,
        data = data,
        env = env,
        visibility = visibility,
    )

    # 3. Unit tests (if defined)
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

    # 4. Integration tests (if defined)
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

    # 5. OCI image targets (if in apps/ directory)
    if package_path.startswith("apps/"):
        # Auto-infer repository from package path
        if not image_repository:
            repo_suffix = package_path[len("apps/"):]
            image_repository = "nexus.gillouche.homelab/docker-hosted/{}".format(repo_suffix)

        # Package source code into tar for OCI layer
        pkg_tar(
            name = name + "_src_layer",
            srcs = srcs,
            package_dir = "/app/src",
            strip_prefix = "src",
        )

        # Package the py_binary (includes deps via runfiles)
        # Note: This packages the executable and its runfiles
        pkg_tar(
            name = name + "_bin_layer",
            srcs = [":" + name],
            package_dir = "/app",
            include_runfiles = True,
        )

        # Create OCI image
        oci_image(
            name = name + "_image",
            base = base_image,
            tars = [
                ":" + name + "_src_layer",
                ":" + name + "_bin_layer",
            ],
            entrypoint = ["python", "-m", "main"],
            workdir = "/app/src",
            env = dict({
                "PYTHONPATH": "/app/src",
                "PYTHONUNBUFFERED": "1",
            }, **env),
            labels = {
                "org.opencontainers.image.source": "https://github.com/gillouche/playground",
                "org.opencontainers.image.title": name,
                "org.opencontainers.image.description": "{} container image".format(name),
            },
            visibility = visibility,
        )

        # OCI push to registry
        oci_push(
            name = name + "_push",
            image = ":" + name + "_image",
            repository = image_repository,
            visibility = visibility,
        )

        # Load to local Docker daemon
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
