#!/usr/bin/env python3

import argparse
import os
import re
import shutil
import subprocess
import sys
import yaml

# Import validation utilities
from validation import (
    validate_version,
    validate_app_exists,
    validate_frozen_version_exists,
    validate_environment,
)


def parse_bom_images(path):
    """Parse BOM to extract component:tag pairs."""
    with open(path, 'r') as f:
        bom = yaml.safe_load(f)

    components = {}
    images = bom.get('images', {})
    for component, data in images.items():
        if isinstance(data, dict) and 'tag' in data:
            components[component] = data['tag']

    return components

def update_kustomization(app_name, env, images):
    """Update kustomization files for the app with rollback versions."""
    kustomization_path = f"apps/{app_name}/deploy/{env}/kustomization.yaml"

    if not os.path.exists(kustomization_path):
        print(f"Warning: {kustomization_path} not found")
        return

    with open(kustomization_path, 'r') as f:
        content = f.read()

    updated = False
    for component, tag in images.items():
        # Update newTag
        # Matches: - name: .../app/component
        #          newTag: ...
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
        with open(kustomization_path, 'w') as f:
            f.write(content)

def rollback(env, app, version):
    """Rollback environment to specific version."""
    archived_bom = f"releases/versions/{app}/{version}.yaml"
    head_bom = f"releases/{env}/{app}.yaml"

    print(f"Rolling back {app} in {env} to {version}...")

    # Copy archived BOM to HEAD
    shutil.copy(archived_bom, head_bom)
    print(f"  Copied {archived_bom} -> {head_bom}")

    # Update kustomization files
    images = parse_bom_images(head_bom)
    update_kustomization(app, env, images)

    print(f"\nRollback complete! {app} in {env} is now at {version}")
    print(f"Images:")
    for comp, tag in images.items():
        print(f"  - {comp}: {tag}")

    print("Regenerating manifests...")
    for comp in images.keys():
        print(f"  Regenerating {comp} for {env}...")
        subprocess.run(
            ["bazel", "run", "//tools:gen_manifests", "--", "--env", env, app, comp],
            capture_output=False,
        )

def main():
    parser = argparse.ArgumentParser(description="Rollback Test or Prod environment to archived version")
    parser.add_argument("--env", required=True, choices=["test", "prod"], help="Environment to rollback (test/prod)")
    parser.add_argument("--app", required=True, help="App name (e.g. demo-app)")
    parser.add_argument("--version", required=True, help="Version to rollback to (e.g., v1.0.0)")

    args = parser.parse_args()

    workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace_dir:
        os.chdir(workspace_dir)

    # Validate inputs before proceeding
    validate_version(args.version)
    validate_app_exists(args.app)
    validate_environment(args.env, allowed=["test", "prod"])
    validate_frozen_version_exists(args.app, args.version)

    rollback(args.env, args.app, args.version)

if __name__ == "__main__":
    main()
