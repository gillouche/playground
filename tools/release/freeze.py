#!/usr/bin/env python3

import argparse
import os
import subprocess
import json
import urllib.request
import urllib.error
import ssl
import sys
import datetime

# Import validation utilities
from validation import (
    validate_version,
    validate_app_exists,
    list_available_components,
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
    """
    Find the latest reachable git tag matching {app}/{component}/v*
    Returns (tag_string, version, commit_sha, timestamp)
    """
    # List all tags matching pattern
    # pattern: app/component/v*
    match_pattern = f"{app}/{component}/v*"
    
    try:
        # Get all matching tags sorted by creatordate
        # format: objectname refname
        cmd = ["git", "tag", "--list", match_pattern, "--sort=-creatordate", "--format=%(refname:short)"]
        output = subprocess.check_output(cmd, encoding="utf-8").strip()
        
        if not output:
            return None
        
        # Iterate tags to find the first one reachable from HEAD
        for tag_name in output.splitlines():
            # Resolve commit SHA (handles annotated tags)
            try:
                sha = subprocess.check_output(["git", "rev-list", "-n", "1", tag_name], encoding="utf-8").strip()
            except subprocess.CalledProcessError:
                continue
            
            # Check reachability
            rc = subprocess.call(["git", "merge-base", "--is-ancestor", sha, "HEAD"])
            if rc == 0:
                # Extract version
                # tag_name: app/component/v1.0.0 -> v1.0.0
                version = tag_name.split("/")[-1]
                
                # Get timestamp
                ts = subprocess.check_output(["git", "show", "-s", "--format=%cI", sha], encoding="utf-8").strip()
                
                return {
                    "tag": tag_name,
                    "version": version,
                    "commit": sha,
                    "created_at": ts
                }
                
        return None
        
    except subprocess.CalledProcessError:
        return None

def verify_image_in_nexus(app, component, version, ssl_context):
    """
    Verify image exists in Nexus with the version tag.
    Returns (ref, digest) or None
    """
    # Nexus path: docker-hosted/{app}/{component}
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

def freeze_app(app, version):
    workspace = os.environ.get("BUILD_WORKSPACE_DIRECTORY", ".")
    app_dir = os.path.join(workspace, "apps", app)
    
    if not os.path.exists(app_dir):
        print(f"Error: App directory not found: {app_dir}")
        sys.exit(1)
        
    print(f"Freezing {app} {version}...")
    
    # 1. Scan components
    components = []
    for d in os.listdir(app_dir):
        full_path = os.path.join(app_dir, d)
        if os.path.isdir(full_path) and d != "deploy":
             # Heuristic: Valid component has BUILD file
             if os.path.exists(os.path.join(full_path, "BUILD.bazel")) or \
                os.path.exists(os.path.join(full_path, "BUILD")):
                 components.append(d)
    
    if not components:
        print("Error: No components found.")
        sys.exit(1)
        
    print(f"Found components: {', '.join(components)}")
    
    bom_data = {
        "release": {
            "version": version,
            "app": app,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        },
        "images": {}
    }
    
    # Resolving CA Cert
    ca_cert = None
    
    # 1. Check workspace ca-bundle.pem
    if workspace:
        repo_ca = os.path.join(workspace, "ca-bundle.pem")
        if os.path.exists(repo_ca):
            ca_cert = repo_ca
            
    # 2. Check env var
    if not ca_cert:
        ca_cert = os.environ.get("SSL_CERT_FILE")

    ssl_ctx = create_ssl_context(ca_cert)
    
    errors = []
    
    for comp in components:
        print(f"Analyzing {comp}...")
        
        # 2. Find reachable tag
        tag_info = get_latest_reachable_tag(app, comp)
        
        if not tag_info:
            print(f"  ERROR: No reachable release tag found for {app}/{comp}/v*")
            errors.append(f"{comp}: No release tag")
            continue
            
        print(f"  Found tag: {tag_info['tag']} ({tag_info['commit'][:7]})")
        
        # 3. Verify image in Nexus
        ref, digest = verify_image_in_nexus(app, comp, tag_info['version'], ssl_ctx)
        
        if not ref:
            print(f"  ERROR: Image not found in Nexus: {app}/{comp}:{tag_info['version']}")
            print(f"  (Did the release workflow run for {tag_info['tag']}?)")
            errors.append(f"{comp}: Image missing")
            continue
            
        print(f"  Verified Image: {digest[:12]}...")
        
        bom_data["images"][comp] = {
            "tag": tag_info['version'], # promote.py uses this for replacement
            "full_tag": tag_info['tag'],
            "commit": tag_info['commit'],
            "image": {
                "ref": ref,
                "digest": digest
            }
        }
        
    if errors:
        print("\nFreeze FAILED with errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
        
    # 4. Generate BOM
    
    output_lines = []
    output_lines.append(f"metadata:")
    output_lines.append(f"  app: {bom_data['release']['app']}")
    output_lines.append(f"  version: {bom_data['release']['version']}")
    output_lines.append(f"  created_at: {bom_data['release']['created_at']}")
    output_lines.append("")
    output_lines.append("images:")
    
    for comp, data in bom_data["images"].items():
        output_lines.append(f"  {comp}:")
        output_lines.append(f"    tag: {data['tag']}")
        output_lines.append(f"    commit: {data['commit']}")
        output_lines.append(f"    full_tag: {data['full_tag']}")
        output_lines.append(f"    image:")
        output_lines.append(f"      ref: {data['image']['ref']}")
        output_lines.append(f"      digest: {data['image']['digest']}")
    
    output_content = "\n".join(output_lines) + "\n"
    
    # Updated path logic: releases/versions/<app>/<version>.yaml
    dest_path = os.path.join(workspace, f"releases/versions/{app}/{version}.yaml")
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
    with open(dest_path, 'w') as f:
        f.write(output_content)
        
    print(f"\nFreeze SUCCESS: {dest_path}")
    print(output_content)

def main():
    parser = argparse.ArgumentParser(description="Freeze App Release")
    parser.add_argument("--app", required=True, help="App name")
    parser.add_argument("--version", required=True, help="Release version (e.g. v1.0.0)")

    args = parser.parse_args()

    # Validate inputs before proceeding
    validate_version(args.version)
    validate_app_exists(args.app)

    freeze_app(args.app, args.version)

if __name__ == "__main__":
    main()
