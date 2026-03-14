#!/usr/bin/env python3

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from validation import (
    validate_app_exists,
    validate_environment,
    validate_frozen_version_exists,
    validate_version,
)


def run_command(cmd, check=True):
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}")
        if result.stderr:
            print(f"Error: {result.stderr}")
        return None
    return result


def git_add(paths):
    if isinstance(paths, str):
        paths = [paths]
    result = run_command(["git", "add", *paths], check=False)
    return result is not None and result.returncode == 0


def git_commit(message):
    result = run_command(["git", "commit", "-m", message], check=False)
    if result and result.returncode == 0:
        return True
    if result and "nothing to commit" in result.stdout:
        print("Nothing to commit - files may already be committed")
        return True
    return False


def _parse_bom_images(source_bom):
    with source_bom.open() as f:
        bom = yaml.safe_load(f)

    images = {}
    for component, data in bom.get("images", {}).items():
        if not isinstance(data, dict):
            continue
        images[component] = {
            "tag": data.get("tag"),
            "commit": data.get("commit"),
            "full_tag": data.get("full_tag"),
        }
        if "image" in data and isinstance(data["image"], dict):
            images[component]["image_ref"] = data["image"].get("ref")
            images[component]["image_digest"] = data["image"].get("digest")
    return images


def _commit_promotion(target_env, app, version):
    print("\nCommitting changes to git...")
    paths_to_add = [f"releases/{target_env}/{app}.yaml", f"apps/{app}/deploy/{target_env}/"]

    if not git_add(paths_to_add):
        print("Warning: Failed to stage files for commit")
        return

    commit_message = f"release: promote {app} {version} to {target_env}"
    if git_commit(commit_message):
        print(f"Created commit: {commit_message}")
    else:
        print("Warning: Failed to create commit")


def promote_app(target_env, app, version, commit=False):
    source_bom = Path(f"releases/versions/{app}/{version}.yaml")
    target_bom_latest = Path(f"releases/{target_env}/{app}.yaml")

    print(f"Promoting {app} {version} to {target_env} (Source: {source_bom})...")

    target_bom_latest.parent.mkdir(parents=True, exist_ok=True)
    if target_bom_latest.exists():
        print(f"Updating existing {target_bom_latest}")
    else:
        print(f"Creating new {target_bom_latest}")

    shutil.copy2(source_bom, target_bom_latest)
    print(f"Updated {target_bom_latest} with content from {version}")

    images = _parse_bom_images(source_bom)

    if not images:
        print("Warning: No images found in BOM. Skipping updates.")
    else:
        update_kustomization(app, target_env, images)

        print(f"Regenerating manifests for {target_env}...")

        for comp in images:
            print(f"  Regenerating {comp} for {target_env}...")
            result = subprocess.run(
                ["bazel", "run", "//tools:gen_manifests", "--", "--env", target_env, app, comp],
                capture_output=False,
                check=False,
            )
            if result.returncode != 0:
                print(f"Error generating manifests for {comp}.")
                sys.exit(1)

        update_configmaps(app, target_env, version, images)

    print(f"\nSuccessfully promoted {app} {version} to {target_env}")

    if commit:
        _commit_promotion(target_env, app, version)


def update_configmaps(app_name, env, version, images):
    deploy_dir = Path(f"apps/{app_name}/deploy/{env}")
    if not deploy_dir.exists():
        return

    for filepath in deploy_dir.iterdir():
        if not filepath.name.endswith("-configmap.yaml"):
            continue

        component = filepath.name.replace("-configmap.yaml", "")

        if component not in images:
            continue

        comp_data = images[component]
        print(f"Updating ConfigMap: {filepath}")

        lines = filepath.read_text().splitlines(keepends=True)

        replacements = {
            "APP_VERSION": version,
            "GIT_TAG": comp_data.get("full_tag", "unknown"),
            "GIT_COMMIT": comp_data.get("commit", "unknown"),
            "APP": app_name,
            "COMPONENT": component,
        }

        new_lines = []
        for line in lines:
            updated_line = line
            for key, val in replacements.items():
                if re.match(rf"\s+{key}:", line):
                    updated_line = re.sub(rf"(\s+{key}:).*", rf'\1 "{val}"', line)
            new_lines.append(updated_line)

        filepath.write_text("".join(new_lines))


def update_kustomization(app_name, env, images):
    kustomization_path = Path(f"apps/{app_name}/deploy/{env}/kustomization.yaml")

    if not kustomization_path.exists():
        print(f"Error: {kustomization_path} not found.")
        return

    content = kustomization_path.read_text()

    updated = False

    if "images:" not in content:
        if not content.endswith("\n"):
            content += "\n"
        content += "\nimages:\n"
        updated = True

    for comp, data in images.items():
        tag = data.get("tag")
        if not tag:
            continue

        image_ref = data.get("image_ref")
        if not (image_ref and ":" in image_ref):
            print(f"  Warning: No image_ref found for {comp}, cannot add new entry safely.")
            continue

        repo_name = image_ref.rsplit(":", 1)[0]

        pattern = re.compile(rf"(-\s+name: {re.escape(repo_name)}\s*\n\s+newTag: ).*")

        if pattern.search(content):
            new_content = pattern.sub(rf'\g<1>"{tag}"', content)
            if content != new_content:
                content = new_content
                updated = True
                print(f"  Updated {comp} image -> {tag}")
        else:
            print(f"  Adding missing image entry for {comp}...")

            new_entry = f'  - name: {repo_name}\n    newTag: "{tag}"\n'
            content = content.replace("images:\n", f"images:\n{new_entry}")
            updated = True

    if updated:
        kustomization_path.write_text(content)
        print(f"Saved {kustomization_path}")
    else:
        print("No Kustomization changes needed.")


def main():
    parser = argparse.ArgumentParser(description="Promote app version to next environment")
    parser.add_argument(
        "--target", required=True, choices=["test", "prod"], help="Target environment"
    )
    parser.add_argument("--app", required=True, help="App name (e.g. demo-app)")
    parser.add_argument("--version", required=True, help="Version tag (e.g. v1.0.0)")
    parser.add_argument(
        "--commit", action="store_true", help="Commit changes to git after promotion"
    )

    args = parser.parse_args()

    workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace_dir:
        os.chdir(workspace_dir)

    validate_version(args.version)
    validate_app_exists(args.app)
    validate_environment(args.target, allowed=["test", "prod"])
    validate_frozen_version_exists(args.app, args.version)

    promote_app(args.target, args.app, args.version, commit=args.commit)


if __name__ == "__main__":
    main()
