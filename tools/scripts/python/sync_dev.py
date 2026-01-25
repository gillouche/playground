#!/usr/bin/env python3

import argparse
import os
import re
import json
import urllib.request
import urllib.error
import ssl

NEXUS_URL = "https://nexus.gillouche.homelab"

def create_ssl_context(ca_cert=None):
    if ca_cert:
        print(f"DEBUG: Using CA cert: {ca_cert}")
    if ca_cert:
        print(f"DEBUG: Using CA cert: {ca_cert}")
    else:
        print("DEBUG: Using system default CA certs")
    
    # Use manual context creation to avoid strict flag 'X509_V_FLAG_X509_STRICT' 
    # which rejects CAs with non-critical BasicConstraints
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.check_hostname = True
    
    if ca_cert:
        ctx.load_verify_locations(cafile=ca_cert)
    else:
        ctx.load_default_certs()
        
    return ctx

def query_nexus_latest(app, component, ssl_context=None):
    """Query Nexus for the latest tag and extract git-{sha}."""
    # Nexus path: docker-hosted/{app}/{component}
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
             tags_data = json.loads(tags_response.read().decode('utf-8'))
        
        # Filter tags, excluding 'latest' and 'git-' prefixed tags
        all_tags = [t for t in tags_data.get("tags", []) if t != "latest" and not t.startswith("git-")]
        
        if not all_tags:
            print(f"Warning: No tags found for {component}")
            return None
        
        # Check matching digest
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

        print(f"Warning: Could not correlate :latest digest ({latest_digest}) to any other tag for {component}")
        return all_tags[0] if all_tags else None
        
    except urllib.error.URLError as e:
        print(f"Error querying Nexus for {app}/{component}: {e}")
        return None

def read_bom(app):
    """Read the current Dev BOM."""
    bom_path = f"releases/dev/{app}.yaml"
    if not os.path.exists(bom_path):
        return {}
    
    components = {}
    with open(bom_path, 'r') as f:
        content = f.read()
        # Simple parsing: find component: \n    tag: value
        pattern = re.compile(r"  (\S+):\s*\n\s+tag: (\S+)")
        for match in pattern.finditer(content):
            components[match.group(1)] = match.group(2)
    
    return components

def update_bom(app, component, tag):
    """Update the Dev BOM with new tag."""
    bom_path = f"releases/dev/{app}.yaml"
    
    if os.path.exists(bom_path):
        with open(bom_path, 'r') as f:
            content = f.read()
    else:
        content = ""
    
    # Ensure root key exists
    if "images:" not in content:
        content = "images:\n" + content.lstrip()
    
    # Update existing component or add new
    pattern = re.compile(rf"(\s+{component}:.*\n\s+tag: ).*")
    
    if pattern.search(content):
        # Update existing
        content = pattern.sub(rf"\g<1>{tag}", content)
    else:
        # Append new component
        if not content.endswith("\n"):
            content += "\n"
        content += f"  {component}:\n"
        content += f"    tag: {tag}\n"
    
    with open(bom_path, 'w') as f:
        f.write(content)

def update_kustomization(app, component, tag):
    """Update the kustomization.yaml with new tag."""
    # New structure: apps/{app}/deploy/dev/kustomization.yaml
    kustomization_path = f"apps/{app}/deploy/dev/kustomization.yaml"
    
    if not os.path.exists(kustomization_path):
        print(f"Warning: {kustomization_path} not found. Skipping kustomization update.")
        return
    
    with open(kustomization_path, 'r') as f:
        content = f.read()
    
    # Update newTag for this component
    # Assumes image name: .../app/component
    pattern = re.compile(rf"(-\s+name: .*{app}/{component}(?::\S+)?[\s\n]+newTag: ).*")
    
    if pattern.search(content):
        content = pattern.sub(rf"\g<1>{tag}", content)
        with open(kustomization_path, 'w') as f:
            f.write(content)
    else:
        print(f"Warning: Could not find image entry for {app}/{component} in {kustomization_path}")

def sync_dev(app, component=None, ssl_context=None):
    """Sync Dev environment with Nexus latest."""
    current_bom = read_bom(app)
    
    # If specific component requested, sync it.
    # Otherwise scan apps/{app} for components
    components_to_sync = [component] if component else list(current_bom.keys())
    
    if not components_to_sync and not component:
        app_dir = f"apps/{app}"
        if os.path.exists(app_dir):
            components_to_sync = []
            for d in os.listdir(app_dir):
                full_path = os.path.join(app_dir, d)
                if os.path.isdir(full_path) and d != "deploy":
                    # Heuristic: Components usually have a src directory or BUILD.bazel
                    if os.path.exists(os.path.join(full_path, "src")) or \
                       os.path.exists(os.path.join(full_path, "BUILD.bazel")):
                        components_to_sync.append(d)
    
    if not components_to_sync:
        print(f"No components found for app '{app}'. Please specify --component or check BOM.")
        return
    
    updated_components = []
    
    for comp_name in components_to_sync:
        print(f"Syncing {comp_name}...")
        # Nexus path: docker-hosted/{app}/{component}
        latest_tag = query_nexus_latest(app, comp_name, ssl_context)
        
        if not latest_tag:
            print(f"  Skipped (no tag found)")
            continue
        
        current_tag = current_bom.get(comp_name)
        
        if current_tag == latest_tag:
            print(f"  Already up to date ({latest_tag})")
            continue
        
        print(f"  Updating {current_tag or 'N/A'} -> {latest_tag}")
        update_bom(app, comp_name, latest_tag)
        update_kustomization(app, comp_name, latest_tag)
        updated_components.append(f"{comp_name}: {latest_tag}")
    
    if updated_components:
        print(f"\nUpdated {len(updated_components)} component(s) in releases/dev/{app}.yaml:")
        for update in updated_components:
            print(f"  - {update}")
        
        # Regenerate manifests
        print("Regenerating manifests...")
        ret = os.system("bazelisk run //tools:gen_manifests")
        if ret != 0:
            print("Error generating manifests.")
    else:
        print("\nNo updates needed.")

def main():
    workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace_dir:
        os.chdir(workspace_dir)

    parser = argparse.ArgumentParser(description="Sync Dev BOM with Nexus latest tags")
    parser.add_argument("--app", required=True, help="App name (e.g., demo-app)")
    parser.add_argument("--component", help="Optional: Specific component to sync.")
    parser.add_argument("--ca-cert", help="Path to CA certificate bundle for Nexus")
    args = parser.parse_args()
    
    # Prioritize ca-bundle.pem in workspace if running via Bazel
    workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    ca_cert = args.ca_cert
    
    if not ca_cert and workspace_dir:
        repo_ca = os.path.join(workspace_dir, "ca-bundle.pem")
        if os.path.exists(repo_ca):
            ca_cert = repo_ca

    # Fallback to SSL_CERT_FILE
    if not ca_cert:
        ca_cert = os.environ.get("SSL_CERT_FILE")
    
    ssl_context = create_ssl_context(ca_cert)
    sync_dev(args.app, args.component, ssl_context)

if __name__ == "__main__":
    main()
