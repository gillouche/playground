#!/usr/bin/env python3

import argparse
import datetime
import json
import os
import re
import ssl
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import yaml
from validation import (
    validate_app_exists,
    validate_component_exists,
)

NEXUS_URL = "https://nexus.gillouche.homelab"


def create_ssl_context(ca_cert=None):
    if ca_cert:
        print(f"DEBUG: Using CA cert: {ca_cert}")
    else:
        print("DEBUG: Using system default CA certs")

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.check_hostname = True

    if ca_cert:
        ctx.load_verify_locations(cafile=ca_cert)
    else:
        ctx.load_default_certs()

    return ctx


def query_nexus_latest(app, component, ssl_context=None):
    manifest_url = f"{NEXUS_URL}/v2/docker-hosted/{app}/{component}/manifests/latest"
    headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}

    try:
        req = urllib.request.Request(manifest_url, headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            latest_digest = response.headers.get("docker-content-digest")

        if not latest_digest:
            print(f"Warning: Could not get digest for {app}/{component}:latest")
            return None

        tags_url = f"{NEXUS_URL}/v2/docker-hosted/{app}/{component}/tags/list"
        with urllib.request.urlopen(tags_url, context=ssl_context) as tags_response:
            tags_data = json.loads(tags_response.read().decode("utf-8"))

        all_tags = [
            t for t in tags_data.get("tags", []) if t != "latest" and not t.startswith("git-")
        ]

        if not all_tags:
            print(f"Warning: No tags found for {component}")
            return None

        for tag in all_tags:
            tag_manifest_url = f"{NEXUS_URL}/v2/docker-hosted/{app}/{component}/manifests/{tag}"
            tag_req = urllib.request.Request(tag_manifest_url, headers=headers)
            try:
                with urllib.request.urlopen(tag_req, context=ssl_context) as tag_response:
                    tag_digest = tag_response.headers.get("docker-content-digest")
                    if tag_digest == latest_digest:
                        return tag
            except urllib.error.HTTPError:
                continue

        print(
            f"Warning: Could not correlate :latest digest ({latest_digest}) to any other tag for {component}"
        )
        return all_tags[0] if all_tags else None

    except urllib.error.URLError as e:
        print(f"Error querying Nexus for {app}/{component}: {e}")
        return None


def read_bom(app):
    bom_path = Path(f"releases/dev/{app}.yaml")
    if not bom_path.exists():
        return {}

    with bom_path.open() as f:
        bom = yaml.safe_load(f)

    components = {}
    images = bom.get("images", {}) if bom else {}
    for component, data in images.items():
        if isinstance(data, dict) and "tag" in data:
            components[component] = data["tag"]

    return components


def update_bom(app, component, tag, commit, ssl_context):
    bom_path = Path(f"releases/dev/{app}.yaml")

    ref = f"nexus.gillouche.homelab/docker-hosted/{app}/{component}:{tag}"
    digest = "unknown"

    try:
        manifest_url = f"{NEXUS_URL}/v2/docker-hosted/{app}/{component}/manifests/{tag}"
        headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
        req = urllib.request.Request(manifest_url, headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            digest = response.headers.get("docker-content-digest", "unknown")
    except Exception as e:
        print(f"  Warning: Could not get digest for {component}:{tag} - {e}")

    bom = {
        "metadata": {
            "app": app,
            "version": "dev",
            "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
        },
        "images": {},
    }

    if bom_path.exists():
        with bom_path.open() as f:
            existing_bom = yaml.safe_load(f)
        if existing_bom and "images" in existing_bom:
            bom["images"] = existing_bom["images"]

    full_tag = f"{app}/{component}/{tag}" if not tag.startswith(f"{app}/") else tag
    bom["images"][component] = {
        "tag": tag,
        "commit": commit,
        "full_tag": full_tag,
        "image": {"ref": ref, "digest": digest},
    }

    bom_path.parent.mkdir(parents=True, exist_ok=True)
    with bom_path.open("w") as f:
        yaml.dump(bom, f, default_flow_style=False, sort_keys=False)


def update_kustomization(app, component, tag):
    kustomization_path = Path(f"apps/{app}/deploy/dev/kustomization.yaml")
    if not kustomization_path.exists():
        print(f"Warning: {kustomization_path} not found. Skipping kustomization update.")
        return

    content = kustomization_path.read_text()

    pattern = re.compile(rf"(-\s+name: .*{app}/{component}(?::\S+)?[\s\n]+newTag: ).*")
    if pattern.search(content):
        content = pattern.sub(rf'\g<1>"{tag}"', content)
        kustomization_path.write_text(content)
    else:
        print(f"Warning: Could not find image entry for {app}/{component} in {kustomization_path}")


def get_git_commit(tag):
    try:
        sha = subprocess.check_output(["git", "rev-list", "-n", "1", tag], encoding="utf-8").strip()
        return sha
    except Exception:
        return "unknown"


def update_configmap(app, component, tag, commit):
    configmap_path = Path(f"apps/{app}/deploy/dev/{component}-configmap.yaml")
    if not configmap_path.exists():
        return

    print(f"  Updating ConfigMap: {configmap_path}")

    lines = configmap_path.read_text().splitlines(keepends=True)

    replacements = {
        "APP_VERSION": "dev",
        "COMPONENT_VERSION": tag,
        "GIT_TAG": tag,
        "GIT_COMMIT": commit,
        "APP": app,
        "COMPONENT": component,
    }

    new_lines = []
    for line in lines:
        updated_line = line
        for key, val in replacements.items():
            if re.match(rf"\s+{key}:", line):
                updated_line = re.sub(rf"(\s+{key}:).*", rf'\1 "{val}"', line)
        new_lines.append(updated_line)

    configmap_path.write_text("".join(new_lines))


def _discover_components(app, current_bom):
    components_to_sync = list(current_bom.keys())
    app_dir = Path(f"apps/{app}")
    if app_dir.exists():
        for entry in app_dir.iterdir():
            if not entry.is_dir() or entry.name == "deploy":
                continue
            if (
                (entry / "src").exists() or (entry / "BUILD.bazel").exists()
            ) and entry.name not in components_to_sync:
                components_to_sync.append(entry.name)
    return components_to_sync


def _sync_components(app, components_to_sync, current_bom, ssl_context):
    updated_components = []
    configmap_updates = []

    for comp_name in components_to_sync:
        print(f"Syncing {comp_name}...")
        latest_tag = query_nexus_latest(app, comp_name, ssl_context)

        if not latest_tag:
            print("  Skipped (no tag found)")
            continue

        current_tag = current_bom.get(comp_name)

        if current_tag == latest_tag:
            print(f"  Skipped (already at {latest_tag})")
            continue

        print(f"  Updating {current_tag or 'N/A'} -> {latest_tag}")

        commit_sha = get_git_commit(latest_tag)

        update_bom(app, comp_name, latest_tag, commit_sha, ssl_context)
        update_kustomization(app, comp_name, latest_tag)

        configmap_updates.append(
            {"app": app, "component": comp_name, "tag": latest_tag, "commit": commit_sha}
        )

        updated_components.append(f"{comp_name}: {latest_tag}")

    return updated_components, configmap_updates


def _regenerate_and_apply(app, updated_components, configmap_updates):
    if not updated_components and not configmap_updates:
        print("\nNo updates needed.")
        return

    if updated_components:
        print(f"\nUpdated {len(updated_components)} component(s) in releases/dev/{app}.yaml:")
        for update in updated_components:
            print(f"  - {update}")

    print("Regenerating manifests (dev only)...")

    components_to_regen = set()
    for item in updated_components:
        comp = item.split(":")[0]
        components_to_regen.add(comp)

    for up in configmap_updates:
        components_to_regen.add(up["component"])

    for comp in components_to_regen:
        print(f"  Regenerating {comp} for dev...")
        ret = os.system(f"bazel run //tools:gen_manifests -- --env dev {app} {comp}")
        if ret != 0:
            print(f"Error generating manifests for {comp}.")

    print("\nApplying metadata to generated ConfigMaps...")
    for up in configmap_updates:
        update_configmap(up["app"], up["component"], up["tag"], up["commit"])


def sync_dev(app, component=None, ssl_context=None):
    current_bom = read_bom(app)

    components_to_sync = [component] if component else _discover_components(app, current_bom)

    if not components_to_sync:
        print(f"No components found for app '{app}'. Please specify --component or check BOM.")
        return

    updated_components, configmap_updates = _sync_components(
        app, components_to_sync, current_bom, ssl_context
    )

    _regenerate_and_apply(app, updated_components, configmap_updates)


def main():
    workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace_dir:
        os.chdir(workspace_dir)

    parser = argparse.ArgumentParser(description="Sync Dev BOM with Nexus latest tags")
    parser.add_argument("--app", required=True, help="App name (e.g., demo-app)")
    parser.add_argument("--component", help="Optional: Specific component to sync.")
    parser.add_argument("--ca-cert", help="Path to CA certificate bundle for Nexus")
    args = parser.parse_args()

    validate_app_exists(args.app)
    if args.component:
        validate_component_exists(args.app, args.component)

    workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    ca_cert = args.ca_cert

    if not ca_cert and workspace_dir:
        repo_ca = Path(workspace_dir) / "ca-bundle.pem"
        if repo_ca.exists():
            ca_cert = str(repo_ca)

    if not ca_cert:
        ca_cert = os.environ.get("SSL_CERT_FILE")

    ssl_context = create_ssl_context(ca_cert)
    sync_dev(args.app, args.component, ssl_context)


if __name__ == "__main__":
    main()
