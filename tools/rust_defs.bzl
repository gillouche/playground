"""
Rust application macro for the polyglot monorepo.

This module provides the rust_application macro for building Rust services
with hermetic dependencies, OCI image packaging, and deployment targets.

Usage in BUILD.bazel:
    load("//tools:rust_defs.bzl", "rust_application")
"""

load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load", "oci_push")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_rust//rust:defs.bzl", "rust_binary", "rust_library", "rust_test")
load("//tools:transitions.bzl", "transition_rule")

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
        base_image = "@rust_base_linux_arm64",
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

        transition_rule(
            name = name + "_image_arm64",
            actual = ":" + name + "_image",
            platform = "//tools/platforms:linux_arm64",
            tags = ["manual"],
            visibility = visibility,
        )

        oci_push(
            name = name + "_push",
            image = ":" + name + "_image_arm64",
            repository = image_repository,
            tags = ["manual"],
            visibility = visibility,
        )

        oci_load(
            name = name + "_load",
            image = ":" + name + "_image_arm64",
            repo_tags = ["{}:latest".format(name)],
            tags = ["manual"],
            visibility = visibility,
        )
