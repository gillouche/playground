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
load("@rules_go//go:defs.bzl", "go_binary", "go_library", "go_test")
load("@rules_rust//rust:defs.bzl", "rust_binary", "rust_library", "rust_test")

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
        {name}_lint       - py_test for ruff linting
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

    # 5. Lint target (ruff)
    # Find ruff in test_deps - look for the requirement that contains ruff
    ruff_dep = None
    for dep in test_deps:
        if "ruff" in str(dep):
            ruff_dep = dep
            break

    if ruff_dep:
        py_test(
            name = name + "_lint",
            srcs = ["//tools:ruff_runner.py"] + srcs,
            main = "//tools:ruff_runner.py",
            args = ["--config=pyproject.toml", "src/"],
            data = ["pyproject.toml"] if native.glob(["pyproject.toml"]) else [],
            deps = [ruff_dep],
            imports = ["."],
            size = "small",
            tags = ["lint"],
            visibility = visibility,
        )

    # 6. OCI image targets (if in apps/ directory)
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


def go_application(
        name,
        srcs,
        deps = [],
        importpath = "",
        unit_tests = [],
        integration_tests = [],
        test_deps = [],
        data = [],
        env = {},
        cgo = False,
        base_image = "@distroless_base_linux_arm64",
        image_repository = "",
        visibility = ["//visibility:public"]):
    """
    Creates a Go application with library, binary, tests, and OCI image targets.

    Uses the host Go toolchain from Nix. Dependencies are managed by go_deps.

    Args:
        name: Application name (e.g., "example-go-service")
        srcs: Source files (glob of .go files)
        deps: Runtime dependencies from go_deps
        importpath: Go import path for the package
        unit_tests: Unit test files
        integration_tests: Integration test files
        test_deps: Additional test dependencies
        data: Data files to include
        env: Environment variables for the binary
        cgo: Enable CGO (default: False for easier cross-compilation)
        base_image: OCI base image (default: distroless for ARM64)
        image_repository: Nexus repository path (auto-inferred from package path)
        visibility: Bazel visibility

    Generated targets:
        {name}_lib        - go_library with source code
        {name}            - go_binary executable
        {name}_unit_test  - go_test for unit tests
        {name}_integration_test - go_test for integration tests
        {name}_image      - OCI image
        {name}_push       - oci_push to registry
        {name}_load       - oci_load to local Docker
    """

    package_path = native.package_name()

    if not importpath:
        importpath = "github.com/gillouche/playground/" + package_path

    go_library(
        name = name + "_lib",
        srcs = srcs,
        deps = deps,
        importpath = importpath,
        data = data,
        cgo = cgo,
        visibility = visibility,
    )

    go_binary(
        name = name,
        srcs = srcs,
        deps = deps,
        data = data,
        cgo = cgo,
        pure = "on" if not cgo else "off",  # Pure Go for easy cross-compilation
        visibility = visibility,
    )

    if unit_tests:
        go_test(
            name = name + "_unit_test",
            srcs = unit_tests,
            deps = [":" + name + "_lib"] + test_deps,
            embed = [":" + name + "_lib"],
            size = "small",
            tags = ["unit"],
            visibility = visibility,
        )

    if integration_tests:
        go_test(
            name = name + "_integration_test",
            srcs = integration_tests,
            deps = [":" + name + "_lib"] + test_deps,
            embed = [":" + name + "_lib"],
            size = "medium",
            tags = ["integration"],
            visibility = visibility,
        )

    if package_path.startswith("apps/"):
        if not image_repository:
            repo_suffix = package_path[len("apps/"):]
            image_repository = "nexus.gillouche.homelab/docker-hosted/{}".format(repo_suffix)

        pkg_tar(
            name = name + "_bin_layer",
            srcs = [":" + name],
            package_dir = "/app",
        )

        oci_image(
            name = name + "_image",
            base = base_image,
            tars = [":" + name + "_bin_layer"],
            entrypoint = ["/app/" + name],
            env = env,
            labels = {
                "org.opencontainers.image.source": "https://github.com/gillouche/playground",
                "org.opencontainers.image.title": name,
                "org.opencontainers.image.description": "{} container image".format(name),
            },
            visibility = visibility,
        )

        oci_push(
            name = name + "_push",
            image = ":" + name + "_image",
            repository = image_repository,
            visibility = visibility,
        )

        oci_load(
            name = name + "_load",
            image = ":" + name + "_image",
            repo_tags = ["{}:latest".format(name)],
            visibility = visibility,
        )


def rust_application(
        name,
        srcs,
        deps = [],
        unit_tests = [],
        integration_tests = [],
        test_deps = [],
        data = [],
        env = {},
        edition = "2021",
        base_image = "@distroless_base_linux_arm64",
        image_repository = "",
        visibility = ["//visibility:public"]):
    """
    Creates a Rust application with library, binary, tests, and OCI image targets.

    Uses the host Rust toolchain from Nix. Dependencies are managed by crate_universe.

    Args:
        name: Application name (e.g., "example-rust-service")
        srcs: Source files (glob of .rs files)
        deps: Runtime dependencies from crate_universe
        unit_tests: Unit test files
        integration_tests: Integration test files
        test_deps: Additional test dependencies
        data: Data files to include
        env: Environment variables for the binary
        edition: Rust edition (default: 2021)
        base_image: OCI base image (default: distroless for ARM64)
        image_repository: Nexus repository path (auto-inferred from package path)
        visibility: Bazel visibility

    Generated targets:
        {name}_lib        - rust_library with source code
        {name}            - rust_binary executable
        {name}_unit_test  - rust_test for unit tests
        {name}_integration_test - rust_test for integration tests
        {name}_image      - OCI image
        {name}_push       - oci_push to registry
        {name}_load       - oci_load to local Docker
    """

    package_path = native.package_name()

    lib_srcs = [s for s in srcs if "lib.rs" in s or "/lib/" in s]
    if lib_srcs:
        rust_library(
            name = name + "_lib",
            srcs = lib_srcs,
            deps = deps,
            data = data,
            edition = edition,
            visibility = visibility,
        )

    rust_binary(
        name = name,
        srcs = srcs,
        deps = deps + ([":" + name + "_lib"] if lib_srcs else []),
        data = data,
        edition = edition,
        visibility = visibility,
    )

    if unit_tests:
        rust_test(
            name = name + "_unit_test",
            srcs = unit_tests,
            deps = [":" + name + "_lib"] + test_deps if lib_srcs else deps + test_deps,
            size = "small",
            tags = ["unit"],
            visibility = visibility,
        )

    if integration_tests:
        rust_test(
            name = name + "_integration_test",
            srcs = integration_tests,
            deps = [":" + name + "_lib"] + test_deps if lib_srcs else deps + test_deps,
            size = "medium",
            tags = ["integration"],
            visibility = visibility,
        )

    if package_path.startswith("apps/"):
        if not image_repository:
            repo_suffix = package_path[len("apps/"):]
            image_repository = "nexus.gillouche.homelab/docker-hosted/{}".format(repo_suffix)

        pkg_tar(
            name = name + "_bin_layer",
            srcs = [":" + name],
            package_dir = "/app",
        )

        oci_image(
            name = name + "_image",
            base = base_image,
            tars = [":" + name + "_bin_layer"],
            entrypoint = ["/app/" + name],
            env = env,
            labels = {
                "org.opencontainers.image.source": "https://github.com/gillouche/playground",
                "org.opencontainers.image.title": name,
                "org.opencontainers.image.description": "{} container image".format(name),
            },
            visibility = visibility,
        )

        oci_push(
            name = name + "_push",
            image = ":" + name + "_image",
            repository = image_repository,
            visibility = visibility,
        )

        oci_load(
            name = name + "_load",
            image = ":" + name + "_image",
            repo_tags = ["{}:latest".format(name)],
            visibility = visibility,
        )

def typescript_application(
        name,
        srcs,
        deps = [],
        unit_tests = [],
        integration_tests = [],
        test_deps = [],
        data = [],
        env = {},
        base_image = "@distroless_base_linux_arm64",
        image_repository = "",
        visibility = ["//visibility:public"]):
    """
    Creates a TypeScript application with library, binary, tests, and OCI image targets.

    Uses the host Node.js toolchain from Nix. Dependencies are managed by npm_translate_lock.

    Args:
        name: Application name (e.g., "example-ts-service")
        srcs: Source files (glob of .ts files)
        deps: Runtime dependencies from npm
        unit_tests: Unit test files
        integration_tests: Integration test files
        test_deps: Additional test dependencies
        data: Data files to include
        env: Environment variables for the binary
        base_image: OCI base image (default: distroless for ARM64)
        image_repository: Nexus repository path (auto-inferred from package path)
        visibility: Bazel visibility

    Generated targets:
        {name}_lib        - ts_project with source code
        {name}            - js_binary executable (bundled)
        {name}_unit_test  - js_test for unit tests
        {name}_integration_test - js_test for integration tests
        {name}_image      - OCI image
        {name}_push       - oci_push to registry
        {name}_load       - oci_load to local Docker
    """

    package_path = native.package_name()


    if package_path.startswith("apps/"):
        if not image_repository:
            repo_suffix = package_path[len("apps/"):]
            image_repository = "nexus.gillouche.homelab/docker-hosted/{}".format(repo_suffix)

        pkg_tar(
            name = name + "_bin_layer",
            srcs = [":" + name],
            package_dir = "/app",
        )

        oci_image(
            name = name + "_image",
            base = base_image,
            tars = [":" + name + "_bin_layer"],
            entrypoint = ["node", "/app/" + name + ".js"],
            env = dict({
                "NODE_ENV": "production",
            }, **env),
            labels = {
                "org.opencontainers.image.source": "https://github.com/gillouche/playground",
                "org.opencontainers.image.title": name,
                "org.opencontainers.image.description": "{} container image".format(name),
            },
            visibility = visibility,
        )

        oci_push(
            name = name + "_push",
            image = ":" + name + "_image",
            repository = image_repository,
            visibility = visibility,
        )

        oci_load(
            name = name + "_load",
            image = ":" + name + "_image",
            repo_tags = ["{}:latest".format(name)],
            visibility = visibility,
        )
