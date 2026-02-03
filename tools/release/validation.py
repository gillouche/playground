#!/usr/bin/env python3
"""
Shared validation utilities for release scripts.
"""

import os
import re
import sys

# Semver pattern: v1.0.0, v1.2.3, v10.20.30, etc.
SEMVER_PATTERN = re.compile(r'^v\d+\.\d+\.\d+$')


def validate_version(version, allow_dev=False):
    """
    Validate version format (semver: v1.0.0).

    Args:
        version: Version string to validate
        allow_dev: If True, also accept 'dev' as valid

    Returns:
        True if valid, exits with error if invalid
    """
    if allow_dev and version == "dev":
        return True

    if not SEMVER_PATTERN.match(version):
        print(f"Error: Invalid version format '{version}'")
        print(f"  Expected format: vX.Y.Z (e.g., v1.0.0, v2.1.3)")
        print(f"  Examples: v1.0.0, v1.2.3, v10.0.0")
        sys.exit(1)

    return True


def validate_app_exists(app, workspace=None):
    """
    Validate that an app directory exists.

    Args:
        app: App name (e.g., demo-app)
        workspace: Workspace directory (defaults to current dir)

    Returns:
        True if valid, exits with error if invalid
    """
    workspace = workspace or os.environ.get("BUILD_WORKSPACE_DIRECTORY", ".")
    app_dir = os.path.join(workspace, "apps", app)

    if not os.path.exists(app_dir):
        print(f"Error: App '{app}' not found")
        print(f"  Expected directory: apps/{app}/")

        available = list_available_apps(workspace)
        if available:
            print(f"\n  Available apps:")
            for a in available:
                print(f"    - {a}")
        else:
            print(f"\n  No apps found in apps/ directory")

        sys.exit(1)

    return True


def validate_component_exists(app, component, workspace=None):
    """
    Validate that a component exists within an app.

    Args:
        app: App name
        component: Component name
        workspace: Workspace directory

    Returns:
        True if valid, exits with error if invalid
    """
    workspace = workspace or os.environ.get("BUILD_WORKSPACE_DIRECTORY", ".")
    component_dir = os.path.join(workspace, "apps", app, component)

    if not os.path.exists(component_dir):
        print(f"Error: Component '{component}' not found in app '{app}'")
        print(f"  Expected directory: apps/{app}/{component}/")

        available = list_available_components(app, workspace)
        if available:
            print(f"\n  Available components in '{app}':")
            for c in available:
                print(f"    - {c}")
        else:
            print(f"\n  No components found in apps/{app}/")

        sys.exit(1)

    return True


def validate_frozen_version_exists(app, version, workspace=None):
    """
    Validate that a frozen version BOM exists.

    Args:
        app: App name
        version: Version string
        workspace: Workspace directory

    Returns:
        True if valid, exits with error if invalid
    """
    workspace = workspace or os.environ.get("BUILD_WORKSPACE_DIRECTORY", ".")
    bom_path = os.path.join(workspace, "releases", "versions", app, f"{version}.yaml")

    if not os.path.exists(bom_path):
        print(f"Error: Frozen version '{version}' not found for app '{app}'")
        print(f"  Expected: releases/versions/{app}/{version}.yaml")

        available = list_available_versions(app, workspace)
        if available:
            print(f"\n  Available frozen versions for '{app}':")
            for v in sorted(available, reverse=True):
                print(f"    - {v}")
            print(f"\n  Tip: Run 'bazel run //tools:freeze -- --app {app} --version {version}' first")
        else:
            print(f"\n  No frozen versions found for '{app}'")
            print(f"  Tip: Run 'bazel run //tools:freeze -- --app {app} --version {version}' to create one")

        sys.exit(1)

    return True


def validate_environment(env, allowed=None):
    """
    Validate environment name.

    Args:
        env: Environment name
        allowed: List of allowed environments (defaults to ["dev", "test", "prod"])

    Returns:
        True if valid, exits with error if invalid
    """
    allowed = allowed or ["dev", "test", "prod"]

    if env not in allowed:
        print(f"Error: Invalid environment '{env}'")
        print(f"  Allowed values: {', '.join(allowed)}")
        sys.exit(1)

    return True


def list_available_apps(workspace=None):
    """List all available apps in the workspace."""
    workspace = workspace or os.environ.get("BUILD_WORKSPACE_DIRECTORY", ".")
    apps_dir = os.path.join(workspace, "apps")

    if not os.path.exists(apps_dir):
        return []

    apps = []
    for d in os.listdir(apps_dir):
        full_path = os.path.join(apps_dir, d)
        if os.path.isdir(full_path) and not d.startswith("."):
            # Check if it has components (subdirs with BUILD files)
            has_components = any(
                os.path.isdir(os.path.join(full_path, sub)) and
                sub != "deploy" and
                (os.path.exists(os.path.join(full_path, sub, "BUILD.bazel")) or
                 os.path.exists(os.path.join(full_path, sub, "BUILD")))
                for sub in os.listdir(full_path)
                if os.path.isdir(os.path.join(full_path, sub))
            )
            if has_components:
                apps.append(d)

    return sorted(apps)


def list_available_components(app, workspace=None):
    """List all available components for an app."""
    workspace = workspace or os.environ.get("BUILD_WORKSPACE_DIRECTORY", ".")
    app_dir = os.path.join(workspace, "apps", app)

    if not os.path.exists(app_dir):
        return []

    components = []
    for d in os.listdir(app_dir):
        full_path = os.path.join(app_dir, d)
        if os.path.isdir(full_path) and d != "deploy" and not d.startswith("."):
            # Has BUILD file = valid component
            if os.path.exists(os.path.join(full_path, "BUILD.bazel")) or \
               os.path.exists(os.path.join(full_path, "BUILD")):
                components.append(d)

    return sorted(components)


def list_available_versions(app, workspace=None):
    """List all frozen versions for an app."""
    workspace = workspace or os.environ.get("BUILD_WORKSPACE_DIRECTORY", ".")
    versions_dir = os.path.join(workspace, "releases", "versions", app)

    if not os.path.exists(versions_dir):
        return []

    versions = []
    for f in os.listdir(versions_dir):
        if f.endswith(".yaml"):
            versions.append(f.replace(".yaml", ""))

    return versions
