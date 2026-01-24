#!/usr/bin/env python3

import argparse
import os
import shutil
import re
import sys

def promote_concept(target_env, concept, version):
    """
    Promote a concept version to the target environment.
    
    Logic:
    1. Always source from Dev frozen BOM: releases/dev/{concept}-{version}.yaml
    2. Update target environment latest BOM: releases/{target}/{concept}.yaml
    3. Update apps/{concept}/deploy/{target}/kustomization.yaml with tags from BOM
    4. Regenerate manifests
    """
    
    # Always source from Dev frozen BOM
    source_env = "dev"
        
    source_bom = f"releases/{source_env}/{concept}-{version}.yaml"
    target_bom_latest = f"releases/{target_env}/{concept}.yaml"
    
    print(f"Promoting {concept} {version} to {target_env} (Source: {source_bom})...")
    
    # 1. Validate Source
    if not os.path.exists(source_bom):
        print(f"Error: Source BOM {source_bom} does not exist.")
        print(f"Tip: Run //tools:freeze --concept {concept} --version {version} first.")
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
        # Parse simple yaml manually or use library if available. 
        # Structure:
        # images:
        #   app-name:
        #     tag: git-sha
        
        # Regex to find app blocks
        # Assumes format: "  app-name:\n    tag: value"
        pattern = re.compile(r"  (\S+):\s*\n\s+tag: (\S+)")
        for match in pattern.finditer(content):
            images[match.group(1)] = match.group(2)
            
    if not images:
        print("Warning: No images found in BOM. Skipping Kustomization update.")
    else:
        update_kustomization(concept, target_env, images)
        
        # 5. Regenerate Manifests
        print("Regenerating manifests...")
        ret = os.system("bazelisk run //tools:gen_manifests")
        if ret != 0:
            print("Error generating manifests.")
            sys.exit(1)
            
    print(f"\nSuccessfully promoted {concept} {version} to {target_env}")

def update_kustomization(concept, env, images):
    kustomization_path = f"apps/{concept}/deploy/{env}/kustomization.yaml"
    
    if not os.path.exists(kustomization_path):
        print(f"Error: {kustomization_path} not found.")
        return

    with open(kustomization_path, 'r') as f:
        content = f.read()

    updated = False
    for app, tag in images.items():
        # Kustomize pattern:
        # - name: .../app
        #   newTag: ...
        
        # We look for '- name: .../app' followed by 'newTag: ...'
        # Regex needs to be robust to finding the specific app block
        pattern = re.compile(rf"(-\s+name: .*?{app}.*?\n\s+newTag: ).*")
        
        if pattern.search(content):
            new_content = pattern.sub(rf"\g<1>{tag}", content)
            if content != new_content:
                content = new_content
                updated = True
                print(f"  Updated {app} -> {tag}")
        else:
            print(f"  Warning: Could not find image entry for {app} in kustomization.")
            
    if updated:
        with open(kustomization_path, 'w') as f:
            f.write(content)
        print(f"Saved {kustomization_path}")
    else:
        print("No Kustomization changes needed.")

def main():
    parser = argparse.ArgumentParser(description="Promote concept version to next environment")
    parser.add_argument("--target", required=True, choices=["test", "prod"], help="Target environment")
    parser.add_argument("--concept", required=True, help="Concept name")
    parser.add_argument("--version", required=True, help="Version tag (e.g. v1.0.0)")

    args = parser.parse_args()

    # Bazel workspace handling
    workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace_dir:
        os.chdir(workspace_dir)

    promote_concept(args.target, args.concept, args.version)

if __name__ == "__main__":
    main()
