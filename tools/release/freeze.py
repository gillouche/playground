#!/usr/bin/env python3

import argparse
import datetime
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from validation import (
    validate_app_exists,
    validate_version,
)

NEXUS_URL = "https://nexus.gillouche.homelab"


def create_ssl_context(ca_cert=None):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.check_hostname = True

    if ca_cert:
        ctx.load_verify_locations(cafile=ca_cert)
    else:
        ctx.load_default_certs()

    return ctx


def get_latest_reachable_tag(app, component):
    match_pattern = f"{app}/{component}/v*"

    try:
        cmd = [
            "git",
            "tag",
            "--list",
            match_pattern,
            "--sort=-creatordate",
            "--format=%(refname:short)",
        ]
        output = subprocess.check_output(cmd, encoding="utf-8").strip()

        if not output:
            return None

        for tag_name in output.splitlines():
            try:
                sha = subprocess.check_output(
                    ["git", "rev-list", "-n", "1", tag_name], encoding="utf-8"
                ).strip()
            except subprocess.CalledProcessError:
                continue

            rc = subprocess.call(["git", "merge-base", "--is-ancestor", sha, "HEAD"])
            if rc == 0:
                version = tag_name.split("/")[-1]

                ts = subprocess.check_output(
                    ["git", "show", "-s", "--format=%cI", sha], encoding="utf-8"
                ).strip()

                return {"tag": tag_name, "version": version, "commit": sha, "created_at": ts}

        return None

    except subprocess.CalledProcessError:
        return None


def verify_image_in_nexus(app, component, version, ssl_context):
    manifest_url = f"{NEXUS_URL}/v2/docker-hosted/{app}/{component}/manifests/{version}"
    headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}

    try:
        req = urllib.request.Request(manifest_url, headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            digest = response.headers.get("docker-content-digest")
            ref = f"nexus.gillouche.homelab/docker-hosted/{app}/{component}:{version}"
            return ref, digest
    except urllib.error.HTTPError as e:
        print(f"  Error checking Nexus for {app}/{component}:{version} -> {e}")
        return None, None
    except urllib.error.URLError as e:
        print(f"  Connection error checking Nexus: {e}")
        return None, None


def _resolve_ca_cert(workspace):
    if workspace:
        repo_ca = workspace / "ca-bundle.pem"
        if repo_ca.exists():
            return str(repo_ca)

    return os.environ.get("SSL_CERT_FILE")


def _scan_components(app_dir):
    components = []
    for entry in app_dir.iterdir():
        if not entry.is_dir() or entry.name == "deploy":
            continue
        if (entry / "BUILD.bazel").exists() or (entry / "BUILD").exists():
            components.append(entry.name)
    return components


def _verify_components(app, components, ssl_ctx):
    bom_images = {}
    errors = []

    for comp in components:
        print(f"Analyzing {comp}...")

        tag_info = get_latest_reachable_tag(app, comp)

        if not tag_info:
            print(f"  ERROR: No reachable release tag found for {app}/{comp}/v*")
            errors.append(f"{comp}: No release tag")
            continue

        print(f"  Found tag: {tag_info['tag']} ({tag_info['commit'][:7]})")

        ref, digest = verify_image_in_nexus(app, comp, tag_info["version"], ssl_ctx)

        if not ref:
            print(f"  ERROR: Image not found in Nexus: {app}/{comp}:{tag_info['version']}")
            print(f"  (Did the release workflow run for {tag_info['tag']}?)")
            errors.append(f"{comp}: Image missing")
            continue

        print(f"  Verified Image: {digest[:12]}...")

        bom_images[comp] = {
            "tag": tag_info["version"],
            "full_tag": tag_info["tag"],
            "commit": tag_info["commit"],
            "image": {"ref": ref, "digest": digest},
        }

    return bom_images, errors


def freeze_app(app, version):
    workspace = Path(os.environ.get("BUILD_WORKSPACE_DIRECTORY", "."))
    app_dir = workspace / "apps" / app

    if not app_dir.exists():
        print(f"Error: App directory not found: {app_dir}")
        sys.exit(1)

    print(f"Freezing {app} {version}...")

    components = _scan_components(app_dir)

    if not components:
        print("Error: No components found.")
        sys.exit(1)

    print(f"Found components: {', '.join(components)}")

    bom_data = {
        "release": {
            "version": version,
            "app": app,
            "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
        },
        "images": {},
    }

    ca_cert = _resolve_ca_cert(workspace)
    ssl_ctx = create_ssl_context(ca_cert)

    bom_images, errors = _verify_components(app, components, ssl_ctx)
    bom_data["images"] = bom_images

    if errors:
        print("\nFreeze FAILED with errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    output_lines = [
        "metadata:",
        f"  app: {bom_data['release']['app']}",
        f"  version: {bom_data['release']['version']}",
        f"  created_at: {bom_data['release']['created_at']}",
        "",
        "images:",
    ]

    for comp, data in bom_data["images"].items():
        output_lines.extend(
            [
                f"  {comp}:",
                f"    tag: {data['tag']}",
                f"    commit: {data['commit']}",
                f"    full_tag: {data['full_tag']}",
                "    image:",
                f"      ref: {data['image']['ref']}",
                f"      digest: {data['image']['digest']}",
            ]
        )

    output_content = "\n".join(output_lines) + "\n"

    dest_path = workspace / f"releases/versions/{app}/{version}.yaml"
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    dest_path.write_text(output_content)

    print(f"\nFreeze SUCCESS: {dest_path}")
    print(output_content)


def main():
    parser = argparse.ArgumentParser(description="Freeze App Release")
    parser.add_argument("--app", required=True, help="App name")
    parser.add_argument("--version", required=True, help="Release version (e.g. v1.0.0)")

    args = parser.parse_args()

    validate_version(args.version)
    validate_app_exists(args.app)

    freeze_app(args.app, args.version)


if __name__ == "__main__":
    main()
