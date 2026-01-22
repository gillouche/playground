#!/usr/bin/env python3

import argparse
import os
import re
import requests

NEXUS_URL = "https://nexus.gillouche.homelab"

def query_nexus_latest(concept, app):
    """Query Nexus for the latest tag and extract git-{sha}."""
    # First, get the digest of the :latest tag
    manifest_url = f"{NEXUS_URL}/v2/docker-hosted/{concept}/{app}/manifests/latest"
    headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
    
    try:
        response = requests.get(manifest_url, headers=headers)
        response.raise_for_status()
        
        # Get the digest of :latest
        latest_digest = response.headers.get("docker-content-digest")
        if not latest_digest:
            print(f"Warning: Could not get digest for {app}:latest")
            return None
        
        # Now query all tags to find which git-* tag has the same digest
        tags_url = f"{NEXUS_URL}/v2/docker-hosted/{concept}/{app}/tags/list"
        tags_response = requests.get(tags_url)
        tags_response.raise_for_status()
        tags_data = tags_response.json()
        
        git_tags = [t for t in tags_data.get("tags", []) if t.startswith("git-")]
        
        if not git_tags:
            print(f"Warning: No git-* tags found for {app}")
            return None
        
        # Find which git-* tag matches the latest digest
        for git_tag in git_tags:
            tag_manifest_url = f"{NEXUS_URL}/v2/docker-hosted/{concept}/{app}/manifests/{git_tag}"
            tag_response = requests.get(tag_manifest_url, headers=headers)
            
            if tag_response.ok:
                tag_digest = tag_response.headers.get("docker-content-digest")
                if tag_digest == latest_digest:
                    return git_tag
        
        # Fallback: if we can't correlate by digest, return the first git tag
        # (This assumes latest corresponds to the most recent build)
        print(f"Warning: Could not correlate :latest digest to git tag for {app}, using first git tag")
        return git_tags[0] if git_tags else None
        
    except requests.exceptions.RequestException as e:
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
    
    if not os.path.exists(bom_path):
        # Create new BOM
        with open(bom_path, 'w') as f:
            f.write("images:\n")
            f.write(f"  {app}:\n")
            f.write(f"    tag: {tag}\n")
        return
    
    with open(bom_path, 'r') as f:
        content = f.read()
    
    # Update existing app or add new
    pattern = re.compile(rf"(\s+{app}:.*\n\s+tag: ).*")
    
    if pattern.search(content):
        # Update existing
        content = pattern.sub(rf"\1{tag}", content)
    else:
        # Append new app
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

def sync_dev(concept, app=None):
    """Sync Dev environment with Nexus latest."""
    current_bom = read_bom(concept)
    apps_to_sync = [app] if app else list(current_bom.keys())
    
    # If no apps in BOM and no specific app, try to discover from concept structure
    if not apps_to_sync:
        # Look for apps in apps/{concept}/*
        concept_dir = f"apps/{concept}"
        if os.path.exists(concept_dir):
            apps_to_sync = [d for d in os.listdir(concept_dir) 
                          if os.path.isdir(os.path.join(concept_dir, d))]
    
    if not apps_to_sync:
        print(f"No apps found for concept '{concept}'. Please specify --app or check BOM.")
        return
    
    updated_apps = []
    
    for app_name in apps_to_sync:
        print(f"Syncing {app_name}...")
        latest_tag = query_nexus_latest(concept, app_name)
        
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
    parser = argparse.ArgumentParser(description="Sync Dev BOM with Nexus latest tags")
    parser.add_argument("--concept", required=True, help="Concept name (e.g., demo-concept)")
    parser.add_argument("--app", help="Optional: Specific app to sync. If omitted, syncs all apps in concept.")
    
    args = parser.parse_args()
    sync_dev(args.concept, args.app)

if __name__ == "__main__":
    main()
