#!/usr/bin/env python3

import argparse
import os
import shutil
import re
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


def run_command(cmd, check=True):
    """Run a command using subprocess and return the result."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )
    if check and result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}")
        if result.stderr:
            print(f"Error: {result.stderr}")
        return None
    return result


def git_add(paths):
    """Stage files for commit."""
    if isinstance(paths, str):
        paths = [paths]
    result = run_command(["git", "add"] + paths, check=False)
    return result is not None and result.returncode == 0


def git_commit(message):
    """Create a git commit with the given message."""
    result = run_command(["git", "commit", "-m", message], check=False)
    if result and result.returncode == 0:
        return True
    if result and "nothing to commit" in result.stdout:
        print("Nothing to commit - files may already be committed")
        return True
    return False


def promote_app(target_env, app, version, commit=False):
    """
    Promote an app version to the target environment.

    Logic:
    1. Always source from Dev frozen BOM: releases/dev/{app}-{version}.yaml
    2. Update target environment latest BOM: releases/{target}/{app}.yaml
    3. Update apps/{app}/deploy/{target}/kustomization.yaml with tags from BOM
    4. Regenerate manifests
    5. Optionally commit changes to git
    """

    # Always source from Central Version Store
    source_bom = f"releases/versions/{app}/{version}.yaml"
    target_bom_latest = f"releases/{target_env}/{app}.yaml"

    print(f"Promoting {app} {version} to {target_env} (Source: {source_bom})...")

    # Update Target Latest BOM
    os.makedirs(os.path.dirname(target_bom_latest), exist_ok=True)
    if os.path.exists(target_bom_latest):
        print(f"Updating existing {target_bom_latest}")
    else:
        print(f"Creating new {target_bom_latest}")

    shutil.copy2(source_bom, target_bom_latest)
    print(f"Updated {target_bom_latest} with content from {version}")

    # 3. Parse BOM to get images and metadata
    with open(source_bom, 'r') as f:
        bom = yaml.safe_load(f)

    images = {}
    bom_images = bom.get('images', {})
    for component, data in bom_images.items():
        if isinstance(data, dict):
            images[component] = {
                'tag': data.get('tag'),
                'commit': data.get('commit'),
                'full_tag': data.get('full_tag'),
            }
            # Handle nested 'image' block
            if 'image' in data and isinstance(data['image'], dict):
                images[component]['image_ref'] = data['image'].get('ref')
                images[component]['image_digest'] = data['image'].get('digest')

    if not images:
        print("Warning: No images found in BOM. Skipping updates.")
    else:
        update_kustomization(app, target_env, images)

        # 5. Regenerate Manifests (Target Env Only)
        print(f"Regenerating manifests for {target_env}...")

        for comp in images.keys():
            print(f"  Regenerating {comp} for {target_env}...")
            result = subprocess.run(
                ["bazel", "run", "//tools:gen_manifests", "--", "--env", target_env, app, comp],
                capture_output=False
            )
            if result.returncode != 0:
                print(f"Error generating manifests for {comp}.")
                sys.exit(1)

        # 6. Update ConfigMaps (Metadata) AFTER generation
        # because gen_manifests overwrites them from templates
        update_configmaps(app, target_env, version, images)

    print(f"\nSuccessfully promoted {app} {version} to {target_env}")

    # 7. Optionally commit changes to git
    if commit:
        print("\nCommitting changes to git...")
        paths_to_add = [
            f"releases/{target_env}/{app}.yaml",
            f"apps/{app}/deploy/{target_env}/"
        ]

        if git_add(paths_to_add):
            commit_message = f"release: promote {app} {version} to {target_env}"
            if git_commit(commit_message):
                print(f"Created commit: {commit_message}")
            else:
                print("Warning: Failed to create commit")
        else:
            print("Warning: Failed to stage files for commit")

def update_configmaps(app_name, env, version, images):
    deploy_dir = f"apps/{app_name}/deploy/{env}"
    if not os.path.exists(deploy_dir):
        return

    for filename in os.listdir(deploy_dir):
        if filename.endswith("-configmap.yaml"):
            filepath = os.path.join(deploy_dir, filename)
            component = filename.replace("-configmap.yaml", "")

            if component in images:
                comp_data = images[component]
                print(f"Updating ConfigMap: {filepath}")

                with open(filepath, 'r') as f:
                    lines = f.readlines()

                new_lines = []
                data_section = False

                # We expect simple key-value pairs in 'data:' section
                # If keys don't exist, we should append them?
                # Better: Regex replace existing known keys.

                replacements = {
                    "APP_VERSION": version,
                    "GIT_TAG": comp_data.get("full_tag", "unknown"),
                    "GIT_COMMIT": comp_data.get("commit", "unknown"),
                    "APP": app_name,
                    "COMPONENT": component
                }

                for line in lines:
                    updated_line = line
                    for key, val in replacements.items():
                        # Match "  KEY: value" or "  KEY:"
                        if re.match(rf"\s+{key}:", line):
                             updated_line = re.sub(rf"(\s+{key}:).*", rf"\1 {val}", line)
                    new_lines.append(updated_line)

                with open(filepath, 'w') as f:
                    f.writelines(new_lines)

def update_kustomization(app_name, env, images):
    kustomization_path = f"apps/{app_name}/deploy/{env}/kustomization.yaml"

    if not os.path.exists(kustomization_path):
        print(f"Error: {kustomization_path} not found.")
        return

    with open(kustomization_path, 'r') as f:
        content = f.read()

    updated = False

    # Check for images section
    if "images:" not in content:
        # naive append if missing, though usually it exists
        if not content.endswith("\n"): content += "\n"
        content += "\nimages:\n"
        updated = True

    for comp, data in images.items():
        tag = data.get("tag")
        if not tag: continue

        # extract repo from image_ref or full_tag or hardcoded assumption
        # image_ref = "nexus.../name:tag" -> we want "nexus.../name"
        image_ref = data.get("image_ref")
        if image_ref and ":" in image_ref:
            repo_name = image_ref.rsplit(":", 1)[0]
        else:
             # Fallback if image_ref parsing failed (should not happen with new parser)
             print(f"  Warning: No image_ref found for {comp}, cannot add new entry safely.")
             continue

        # Kustomize pattern to match existing entry
        # - name: nexus.../demo-app/greeting-service
        #   newTag: ...
        # match strictly on the repo name
        pattern = re.compile(rf"(-\s+name: {re.escape(repo_name)}\s*\n\s+newTag: ).*")

        if pattern.search(content):
            new_content = pattern.sub(rf'\g<1>"{tag}"', content)
            if content != new_content:
                content = new_content
                updated = True
                print(f"  Updated {comp} image -> {tag}")
        else:
            print(f"  Adding missing image entry for {comp}...")
            # Append to images section
            # We assume 'images:' exists (ensured above)
            # Find the line "images:" and append after it? Or at the end of the block?
            # Kustomize doesn't strictly require order, but indentation matters.
            # Safe bet: append to the end of the `images:` list if possible, or just replace `images:` with `images:\n  - name...`
            # But regex sub is cleaner if we just find `images:` and insert after.

            new_entry = f'  - name: {repo_name}\n    newTag: "{tag}"\n'
            content = content.replace("images:\n", f"images:\n{new_entry}")
            updated = True

    if updated:
        with open(kustomization_path, 'w') as f:
            f.write(content)
        print(f"Saved {kustomization_path}")
    else:
        print("No Kustomization changes needed.")

def main():
    parser = argparse.ArgumentParser(description="Promote app version to next environment")
    parser.add_argument("--target", required=True, choices=["test", "prod"], help="Target environment")
    parser.add_argument("--app", required=True, help="App name (e.g. demo-app)")
    parser.add_argument("--version", required=True, help="Version tag (e.g. v1.0.0)")
    parser.add_argument("--commit", action="store_true", help="Commit changes to git after promotion")

    args = parser.parse_args()

    # Bazel workspace handling
    workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace_dir:
        os.chdir(workspace_dir)

    # Validate inputs before proceeding
    validate_version(args.version)
    validate_app_exists(args.app)
    validate_environment(args.target, allowed=["test", "prod"])
    validate_frozen_version_exists(args.app, args.version)

    promote_app(args.target, args.app, args.version, commit=args.commit)

if __name__ == "__main__":
    main()
