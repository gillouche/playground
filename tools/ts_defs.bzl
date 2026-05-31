"""
TypeScript application macro for the polyglot monorepo.

This module provides the typescript_application macro for building TypeScript services
with hermetic dependencies, OCI image packaging, and deployment targets.

Usage in BUILD.bazel:
    load("//tools:ts_defs.bzl", "typescript_application")

Note: TypeScript compilation requires ts_project which needs additional setup.
See libs/templates/typescript-service for a complete example.
"""

load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load", "oci_push")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//tools:transitions.bzl", "transition_rule")

def typescript_application(
        name,
        srcs,
        deps = [],
        unit_tests = [],
        integration_tests = [],
        test_deps = [],
        data = [],
        env = {},
        base_image = "@typescript_base_linux_arm64",
        image_repository = "",
        visibility = ["//visibility:public"]):
    """
    Creates a TypeScript application OCI image targets.

    Uses the host Node.js toolchain from Nix. Dependencies are managed by npm_translate_lock.

    Note: This macro only creates OCI image targets. TypeScript compilation requires
    ts_project which should be defined in the service's BUILD.bazel file.
    See libs/templates/typescript-service for a complete example.

    Args:
        name: Application name (e.g., "example-ts-service")
        srcs: Compiled JS files (output of ts_project or js_binary)
        deps: Runtime dependencies from npm
        unit_tests: Unit test files (unused, define separately)
        integration_tests: Integration test files (unused, define separately)
        test_deps: Additional test dependencies (unused, define separately)
        data: Data files to include
        env: Environment variables for the binary
        base_image: OCI base image (default: distroless for ARM64)
        image_repository: Nexus repository path (auto-inferred from package path)
        visibility: Bazel visibility

    Generated targets:
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
            srcs = srcs,
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
