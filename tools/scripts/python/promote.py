#!/usr/bin/env python3

import argparse
import os
import shutil
import re
import sys

def promote_app(target_env, app, version):
    """
    Promote an app version to the target environment.
    
    Logic:
    1. Always source from Dev frozen BOM: releases/dev/{app}-{version}.yaml
    2. Update target environment latest BOM: releases/{target}/{app}.yaml
    3. Update apps/{app}/deploy/{target}/kustomization.yaml with tags from BOM
    4. Regenerate manifests
    """
    
    # Always source from Central Version Store
    source_bom = f"releases/versions/{app}/{version}.yaml"
    target_bom_latest = f"releases/{target_env}/{app}.yaml"
    
    print(f"Promoting {app} {version} to {target_env} (Source: {source_bom})...")
    
    # 1. Validate Source
    if not os.path.exists(source_bom):
        print(f"Error: Source BOM {source_bom} does not exist.")
        print(f"Tip: Run //tools:freeze --app {app} --version {version} first.")
        sys.exit(1)
        
    # 2. Update Target Latest BOM
    os.makedirs(os.path.dirname(target_bom_latest), exist_ok=True)
    if os.path.exists(target_bom_latest):
        print(f"Updating existing {target_bom_latest}")
    else:
        print(f"Creating new {target_bom_latest}")
        
    shutil.copy2(source_bom, target_bom_latest)
    print(f"Updated {target_bom_latest} with content from {version}")
    
    # 3. Parse BOM to get images for Kustomization update
    images = {}
    with open(source_bom, 'r') as f:
        content = f.read()
        
    # Regex to find component blocks indent 2 spaces
    #   component:
    #     tag: value
    pattern = re.compile(r"  (\S+):\s*\n\s+tag: (\S+)")
    for match in pattern.finditer(content):
        # Exclude metadata keys if they accidentally match (unlikely with 'tag' requirement)
        key = match.group(1)
        val = match.group(2)
        if key not in ["metadata", "concept", "version", "app"]:
            images[key] = val
            
    if not images:
        print("Warning: No images found in BOM (or regex failed). Skipping Kustomization update.")
    else:
        update_kustomization(app, target_env, images)
        
        # 5. Regenerate Manifests
        print("Regenerating manifests...")
        ret = os.system("bazelisk run //tools:gen_manifests")
        if ret != 0:
            print("Error generating manifests.")
            sys.exit(1)
            
    print(f"\nSuccessfully promoted {app} {version} to {target_env}")

def update_kustomization(app_name, env, images):
    kustomization_path = f"apps/{app_name}/deploy/{env}/kustomization.yaml"
    
    if not os.path.exists(kustomization_path):
        print(f"Error: {kustomization_path} not found.")
        return

    with open(kustomization_path, 'r') as f:
        content = f.read()

    updated = False
    for comp, tag in images.items():
        # Kustomize pattern:
        # - name: .../app/comp
        #   newTag: ...

        # In kustomization we have:
        #   - name: nexus.../demo-app/greeting-service
        # So we match 'greeting-service' in the name line.
        
        pattern = re.compile(rf"(-\s+name: .*?{comp}.*?\n\s+newTag: ).*")
        
        if pattern.search(content):
            new_content = pattern.sub(rf"\g<1>{tag}", content)
            if content != new_content:
                content = new_content
                updated = True
                print(f"  Updated {comp} -> {tag}")
        else:
            print(f"  Warning: Could not find image entry for {comp} in kustomization.")
            
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

    args = parser.parse_args()

    # Bazel workspace handling
    workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace_dir:
        os.chdir(workspace_dir)

    promote_app(args.target, args.app, args.version)

if __name__ == "__main__":
    main()
