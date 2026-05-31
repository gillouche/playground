#!/usr/bin/env python3

import os
import re
import sys
from pathlib import Path

SEMVER_PATTERN = re.compile(r"^v\d+\.\d+\.\d+$")


def validate_version(version, allow_dev=False):
    if allow_dev and version == "dev":
        return True

    if not SEMVER_PATTERN.match(version):
        print(f"Error: Invalid version format '{version}'")
        print("  Expected format: vX.Y.Z (e.g., v1.0.0, v2.1.3)")
        print("  Examples: v1.0.0, v1.2.3, v10.0.0")
        sys.exit(1)

    return True


def validate_app_exists(app, workspace=None):
    workspace = Path(workspace or os.environ.get("BUILD_WORKSPACE_DIRECTORY", "."))
    app_dir = workspace / "apps" / app

    if not app_dir.exists():
        print(f"Error: App '{app}' not found")
        print(f"  Expected directory: apps/{app}/")

        available = list_available_apps(str(workspace))
        if available:
            print("\n  Available apps:")
            for a in available:
                print(f"    - {a}")
        else:
            print("\n  No apps found in apps/ directory")

        sys.exit(1)

    return True


def validate_component_exists(app, component, workspace=None):
    workspace = Path(workspace or os.environ.get("BUILD_WORKSPACE_DIRECTORY", "."))
    component_dir = workspace / "apps" / app / component

    if not component_dir.exists():
        print(f"Error: Component '{component}' not found in app '{app}'")
        print(f"  Expected directory: apps/{app}/{component}/")

        available = list_available_components(app, str(workspace))
        if available:
            print(f"\n  Available components in '{app}':")
            for c in available:
                print(f"    - {c}")
        else:
            print(f"\n  No components found in apps/{app}/")

        sys.exit(1)

    return True


def validate_frozen_version_exists(app, version, workspace=None):
    workspace = Path(workspace or os.environ.get("BUILD_WORKSPACE_DIRECTORY", "."))
    bom_path = workspace / "releases" / "versions" / app / f"{version}.yaml"

    if not bom_path.exists():
        print(f"Error: Frozen version '{version}' not found for app '{app}'")
        print(f"  Expected: releases/versions/{app}/{version}.yaml")

        available = list_available_versions(app, str(workspace))
        if available:
            print(f"\n  Available frozen versions for '{app}':")
            for v in sorted(available, reverse=True):
                print(f"    - {v}")
            print(
                f"\n  Tip: Run 'bazel run //tools:freeze -- --app {app} --version {version}' first"
            )
        else:
            print(f"\n  No frozen versions found for '{app}'")
            print(
                f"  Tip: Run 'bazel run //tools:freeze -- --app {app} --version {version}' to create one"
            )

        sys.exit(1)

    return True


def validate_environment(env, allowed=None):
    allowed = allowed or ["dev", "test", "prod"]

    if env not in allowed:
        print(f"Error: Invalid environment '{env}'")
        print(f"  Allowed values: {', '.join(allowed)}")
        sys.exit(1)

    return True


def _has_build_file(directory):
    return (directory / "BUILD.bazel").exists() or (directory / "BUILD").exists()


def list_available_apps(workspace=None):
    workspace = Path(workspace or os.environ.get("BUILD_WORKSPACE_DIRECTORY", "."))
    apps_dir = workspace / "apps"

    if not apps_dir.exists():
        return []

    apps = []
    for entry in apps_dir.iterdir():
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        has_components = any(
            sub.is_dir() and sub.name != "deploy" and _has_build_file(sub)
            for sub in entry.iterdir()
            if sub.is_dir()
        )
        if has_components:
            apps.append(entry.name)

    return sorted(apps)


def list_available_components(app, workspace=None):
    workspace = Path(workspace or os.environ.get("BUILD_WORKSPACE_DIRECTORY", "."))
    app_dir = workspace / "apps" / app

    if not app_dir.exists():
        return []

    components = []
    for entry in app_dir.iterdir():
        if (
            entry.is_dir()
            and entry.name != "deploy"
            and not entry.name.startswith(".")
            and _has_build_file(entry)
        ):
            components.append(entry.name)

    return sorted(components)


def list_available_versions(app, workspace=None):
    workspace = Path(workspace or os.environ.get("BUILD_WORKSPACE_DIRECTORY", "."))
    versions_dir = workspace / "releases" / "versions" / app

    if not versions_dir.exists():
        return []

    return [f.stem for f in versions_dir.iterdir() if f.suffix == ".yaml"]
