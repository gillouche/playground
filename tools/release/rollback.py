#!/usr/bin/env python3

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path

import yaml
from validation import (
    validate_app_exists,
    validate_environment,
    validate_frozen_version_exists,
    validate_version,
)


def parse_bom_images(path):
    bom_path = Path(path)
    with bom_path.open() as f:
        bom = yaml.safe_load(f)

    components = {}
    images = bom.get("images", {})
    for component, data in images.items():
        if isinstance(data, dict) and "tag" in data:
            components[component] = data["tag"]

    return components


def update_kustomization(app_name, env, images):
    kustomization_path = Path(f"apps/{app_name}/deploy/{env}/kustomization.yaml")

    if not kustomization_path.exists():
        print(f"Warning: {kustomization_path} not found")
        return

    content = kustomization_path.read_text()

    updated = False
    for component, tag in images.items():
        pattern = re.compile(rf"(-\s+name: .*{app_name}/{component}.*?\n\s+newTag: ).*")

        if pattern.search(content):
            new_content = pattern.sub(rf'\1"{tag}"', content)
            if content != new_content:
                content = new_content
                updated = True
                print(f"  Updated {component} kustomization -> {tag}")
        else:
            print(f"  Warning: Could not find image entry for {component}")

    if updated:
        kustomization_path.write_text(content)


def rollback(env, app, version):
    archived_bom = f"releases/versions/{app}/{version}.yaml"
    head_bom = f"releases/{env}/{app}.yaml"

    print(f"Rolling back {app} in {env} to {version}...")

    shutil.copy(archived_bom, head_bom)
    print(f"  Copied {archived_bom} -> {head_bom}")

    images = parse_bom_images(head_bom)
    update_kustomization(app, env, images)

    print(f"\nRollback complete! {app} in {env} is now at {version}")
    print("Images:")
    for comp, tag in images.items():
        print(f"  - {comp}: {tag}")

    print("Regenerating manifests...")
    for comp in images:
        print(f"  Regenerating {comp} for {env}...")
        subprocess.run(
            ["bazel", "run", "//tools:gen_manifests", "--", "--env", env, app, comp],
            capture_output=False,
            check=False,
        )


def main():
    parser = argparse.ArgumentParser(
        description="Rollback Test or Prod environment to archived version"
    )
    parser.add_argument(
        "--env", required=True, choices=["test", "prod"], help="Environment to rollback (test/prod)"
    )
    parser.add_argument("--app", required=True, help="App name (e.g. demo-app)")
    parser.add_argument("--version", required=True, help="Version to rollback to (e.g., v1.0.0)")

    args = parser.parse_args()

    workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace_dir:
        os.chdir(workspace_dir)

    validate_version(args.version)
    validate_app_exists(args.app)
    validate_environment(args.env, allowed=["test", "prod"])
    validate_frozen_version_exists(args.app, args.version)

    rollback(args.env, args.app, args.version)


if __name__ == "__main__":
    main()
