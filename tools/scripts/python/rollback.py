#!/usr/bin/env python3

import argparse
import os
import re
import shutil
import sys

def parse_bom_images(path):
    """Parse BOM to extract component:tag pairs."""
    with open(path, 'r') as f:
        content = f.read()
    
    components = {}
    pattern = re.compile(r"  (\S+):\s*\n\s+tag: (\S+)")
    for match in pattern.finditer(content):
        components[match.group(1)] = match.group(2)
    
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
            new_content = pattern.sub(rf"\1{tag}", content)
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
    if env not in ["test", "prod"]:
        print(f"Error: --env must be 'test' or 'prod', got '{env}'")
        sys.exit(1)
    
    archived_bom = f"releases/versions/{app}/{version}.yaml"
    head_bom = f"releases/{env}/{app}.yaml"
    
    if not os.path.exists(archived_bom):
        print(f"Error: Archived BOM not found: {archived_bom}")
        print(f"Available versions:")
        # List available versions in central store
        versions_dir = f"releases/versions/{app}"
        if os.path.exists(versions_dir):
            for f in os.listdir(versions_dir):
                if f.endswith(".yaml"):
                    print(f"  - {f.replace('.yaml', '')}")
        sys.exit(1)
    
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
    os.system("bazelisk run //tools:gen_manifests")

def main():
    parser = argparse.ArgumentParser(description="Rollback Test or Prod environment to archived version")
    parser.add_argument("--env", required=True, choices=["test", "prod"], help="Environment to rollback (test/prod)")
    parser.add_argument("--app", required=True, help="App name (e.g. demo-app)")
    parser.add_argument("--version", required=True, help="Version to rollback to (e.g., v1.0.0)")
    
    args = parser.parse_args()
    
    workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace_dir:
        os.chdir(workspace_dir)

    rollback(args.env, args.app, args.version)

if __name__ == "__main__":
    main()
