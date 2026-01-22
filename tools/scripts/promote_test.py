#!/usr/bin/env python3

import argparse
import os
import re

def update_bom(concept, app, version):
    bom_path = f"releases/test/{concept}.yaml"
    os.makedirs(os.path.dirname(bom_path), exist_ok=True)
    
    if not os.path.exists(bom_path):
        with open(bom_path, 'w') as f:
            f.write("images:\n")
            f.write(f"  {app}:\n")
            f.write(f"    tag: {version}\n")
        print(f"Created BOM {bom_path}")
        return

    with open(bom_path, 'r') as f:
        content = f.read()

    # Regex to find the app block and update tag
    # Pattern:   app: \n    tag: old_val
    pattern = re.compile(rf"(\s+{app}:.*\n\s+tag: ).*")
    
    if pattern.search(content):
        new_content = pattern.sub(rf"\g<1>{version}", content)
    else:
        # App not found, append it
        # Needs careful checking if images: block exists
        if "images:" in content:
            new_content = content.rstrip() + f"\n  {app}:\n    tag: {version}\n"
        else:
             new_content = content.rstrip() + f"\nimages:\n  {app}:\n    tag: {version}\n"
    
    if content != new_content:
        with open(bom_path, 'w') as f:
            f.write(new_content)
        print(f"Updated BOM {bom_path}")
    else:
        print(f"No changes needed for BOM {bom_path}")

def update_kustomization(concept, app, version):
    kustomization_path = f"apps/{concept}/deploy/test/kustomization.yaml"
    if not os.path.exists(kustomization_path):
        print(f"Error: {kustomization_path} not found. Please create it first.")
        # allow partial updates if needed -> warning
        return

    with open(kustomization_path, 'r') as f:
        content = f.read()

    # Kustomize image tag replacement
    # - name: .*\/app
    #   newTag: version
    
    # Matches: - name: .../app ... newTag: ...
    # 'name' line comes before 'newTag'.
    pattern = re.compile(rf"(-\s+name: .*?{app}.*?\n\s+newTag: ).*")
    
    if pattern.search(content):
        new_content = pattern.sub(rf"\g<1>{version}", content)
        if content != new_content:
            with open(kustomization_path, 'w') as f:
                f.write(new_content)
            print(f"Updated Kustomization {kustomization_path}")
    else:
        print(f"Warning: Could not find image entry for {app} in {kustomization_path}. Ensure 'newTag' is present.")

def main():
    parser = argparse.ArgumentParser(description="Promote app to Test environment")
    parser.add_argument("--concept", required=True, help="Concept name (e.g. demo-concept)")
    parser.add_argument("--app", required=True, help="App name (e.g. py-app)")
    parser.add_argument("--version", required=True, help="Version tag (e.g. v1.0.0)")
    
    args = parser.parse_args()
    
    # Bazel BUILD_WORKSPACE_DIRECTORY check
    workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace_dir:
        os.chdir(workspace_dir)
        print(f"Running in workspace: {workspace_dir}")
    
    update_bom(args.concept, args.app, args.version)
    update_kustomization(args.concept, args.app, args.version)

if __name__ == "__main__":
    main()
