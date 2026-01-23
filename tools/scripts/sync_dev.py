#!/usr/bin/env python3

import argparse
import os
import re
import json
import urllib.request
import urllib.error
import ssl

NEXUS_URL = "https://nexus.gillouche.homelab"

def create_ssl_context(ca_cert=None, insecure=False):
    if insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    
    ctx = ssl.create_default_context()
    if ca_cert:
        ctx.load_verify_locations(cafile=ca_cert)
    return ctx

def query_nexus_latest(concept, app, ssl_context=None):
    """Query Nexus for the latest tag and extract git-{sha}."""
    manifest_url = f"{NEXUS_URL}/v2/docker-hosted/{concept}/{app}/manifests/latest"
    headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
    
    try:
        req = urllib.request.Request(manifest_url, headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            latest_digest = response.headers.get("docker-content-digest")
            
        if not latest_digest:
            print(f"Warning: Could not get digest for {app}:latest")
            return None
        
        tags_url = f"{NEXUS_URL}/v2/docker-hosted/{concept}/{app}/tags/list"
        with urllib.request.urlopen(tags_url, context=ssl_context) as tags_response:
             tags_data = json.loads(tags_response.read().decode('utf-8'))
        
        git_tags = [t for t in tags_data.get("tags", []) if t.startswith("git-")]
        
        if not git_tags:
            print(f"Warning: No git-* tags found for {app}")
            return None
        
        for git_tag in git_tags:
            tag_manifest_url = f"{NEXUS_URL}/v2/docker-hosted/{concept}/{app}/manifests/{git_tag}"
            tag_req = urllib.request.Request(tag_manifest_url, headers=headers)
            
            try:
                with urllib.request.urlopen(tag_req, context=ssl_context) as tag_response:
                    tag_digest = tag_response.headers.get("docker-content-digest")
                    if tag_digest == latest_digest:
                        return git_tag
            except urllib.error.HTTPError:
                continue

        print(f"Warning: Could not correlate :latest digest to git tag for {app}, using first git tag")
        return git_tags[0] if git_tags else None
        
    except urllib.error.URLError as e:
        print(f"Error querying Nexus for {app}: {e}")
        return None

def read_bom(concept):
    """Read the current Dev BOM."""
    bom_path = f"releases/dev/{concept}.yaml"
    if not os.path.exists(bom_path):
        return {}
    
    apps = {}
    with open(bom_path, 'r') as f:
        content = f.read()
        # Simple parsing: find app: \n    tag: value
        pattern = re.compile(r"  (\S+):\s*\n\s+tag: (git-\S+)")
        for match in pattern.finditer(content):
            apps[match.group(1)] = match.group(2)
    
    return apps

def update_bom(concept, app, tag):
    """Update the Dev BOM with new tag."""
    bom_path = f"releases/dev/{concept}.yaml"
    
def update_bom(concept, app, tag):
    """Update the Dev BOM with new tag."""
    bom_path = f"releases/dev/{concept}.yaml"
    
    if os.path.exists(bom_path):
        with open(bom_path, 'r') as f:
            content = f.read()
    else:
        content = ""
    
    # Ensure root key exists
    if "images:" not in content:
        content = "images:\n" + content.lstrip()
    
    # Update existing app or add new
    pattern = re.compile(rf"(\s+{app}:.*\n\s+tag: ).*")
    
    if pattern.search(content):
        # Update existing
        content = pattern.sub(rf"\1{tag}", content)
    else:
        # Append new app
        # Ensure we append to valid yaml structure
        if not content.endswith("\n"):
            content += "\n"
        content += f"  {app}:\n"
        content += f"    tag: {tag}\n"
    
    with open(bom_path, 'w') as f:
        f.write(content)

def update_kustomization(concept, app, tag):
    """Update the kustomization.yaml with new tag."""
    kustomization_path = f"apps/{concept}/deploy/dev/kustomization.yaml"
    
    if not os.path.exists(kustomization_path):
        print(f"Warning: {kustomization_path} not found. Skipping kustomization update.")
        return
    
    with open(kustomization_path, 'r') as f:
        content = f.read()
    
    # Update newTag for this app
    # Pattern assumes standard kustomization format
    pattern = re.compile(rf"(-\s+name: .*{app}.*?\n\s+newTag: ).*")
    
    if pattern.search(content):
        content = pattern.sub(rf"\1{tag}", content)
        with open(kustomization_path, 'w') as f:
            f.write(content)
    else:
        print(f"Warning: Could not find image entry for {app} in {kustomization_path}")

def sync_dev(concept, app=None, ssl_context=None):
    """Sync Dev environment with Nexus latest."""
    current_bom = read_bom(concept)
    apps_to_sync = [app] if app else list(current_bom.keys())
    
    if not apps_to_sync:
        concept_dir = f"apps/{concept}"
        if os.path.exists(concept_dir):
            apps_to_sync = []
            for d in os.listdir(concept_dir):
                full_path = os.path.join(concept_dir, d)
                if os.path.isdir(full_path):
                    # Heuristic: Apps usually have a src directory or BUILD.bazel
                    if os.path.exists(os.path.join(full_path, "src")) or \
                       os.path.exists(os.path.join(full_path, "BUILD.bazel")):
                        apps_to_sync.append(d)
    
    if not apps_to_sync:
        print(f"No apps found for concept '{concept}'. Please specify --app or check BOM.")
        return
    
    updated_apps = []
    
    for app_name in apps_to_sync:
        print(f"Syncing {app_name}...")
        latest_tag = query_nexus_latest(concept, app_name, ssl_context)
        
        if not latest_tag:
            print(f"  Skipped (no tag found)")
            continue
        
        current_tag = current_bom.get(app_name)
        
        if current_tag == latest_tag:
            print(f"  Already up to date ({latest_tag})")
            continue
        
        print(f"  Updating {current_tag or 'N/A'} -> {latest_tag}")
        update_bom(concept, app_name, latest_tag)
        update_kustomization(concept, app_name, latest_tag)
        updated_apps.append(f"{app_name}: {latest_tag}")
    
    if updated_apps:
        print(f"\nUpdated {len(updated_apps)} app(s) in releases/dev/{concept}.yaml:")
        for update in updated_apps:
            print(f"  - {update}")
    else:
        print("\nNo updates needed.")

def main():
    workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace_dir:
        os.chdir(workspace_dir)

    parser = argparse.ArgumentParser(description="Sync Dev BOM with Nexus latest tags")
    parser.add_argument("--concept", required=True, help="Concept name (e.g., demo-concept)")
    parser.add_argument("--app", help="Optional: Specific app to sync.")
    parser.add_argument("--ca-cert", help="Path to CA certificate bundle for Nexus")
    parser.add_argument("--insecure", action="store_true", help="Skip SSL verification (NOT RECOMMENDED)")
    
    args = parser.parse_args()
    
    # Use args.ca_cert or fallback to SSL_CERT_FILE env var
    ca_cert = args.ca_cert or os.environ.get("SSL_CERT_FILE")
    
    ssl_context = create_ssl_context(ca_cert, args.insecure)
    sync_dev(args.concept, args.app, ssl_context)

if __name__ == "__main__":
    main()
