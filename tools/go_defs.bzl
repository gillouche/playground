"""
Go application macro for the polyglot monorepo.

This module provides the go_application macro for building Go services
with hermetic dependencies, OCI image packaging, and deployment targets.

Usage in BUILD.bazel:
    load("//tools:go_defs.bzl", "go_application")
"""

load("@rules_go//go:defs.bzl", "go_binary", "go_library", "go_test")
load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load", "oci_push")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

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
        pure = "on" if not cgo else "off",
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
