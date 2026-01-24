#!/usr/bin/env python3

import argparse
import os
import re
import sys

def parse_bom_images(path):
    # Returns check: {'app': 'tag'}
    images = {}
    current_app = None
    if not os.path.exists(path):
         print(f"Error: BOM {path} does not exist.")
         sys.exit(1)

    with open(path, 'r') as f:
        for line in f:
            stripped = line.strip()
            # Simple indentation check
            indent = len(line) - len(line.lstrip())
            
            if stripped.startswith("images:"):
                continue
            
            # Assume app name is at indentation 2 (images: is 0, some-app: is 2)
            if indent == 2 and stripped.endswith(":"):
                current_app = stripped[:-1]
                
            # Assume tag is at indentation 4
            if indent == 4 and stripped.startswith("tag:"):
                tag = stripped.split("tag:")[1].strip()
                if current_app:
                    images[current_app] = tag
    return images

def update_prod_bom(concept, images):
    bom_path = f"releases/prod/{concept}.yaml"
    os.makedirs(os.path.dirname(bom_path), exist_ok=True)
    
    with open(bom_path, 'w') as f:
        f.write("images:\n")
        for app, tag in images.items():
            f.write(f"  {app}:\n")
            f.write(f"    tag: {tag}\n")
    print(f"Updated Prod BOM {bom_path}")

def update_kustomization(concept, app, version):
    kustomization_path = f"apps/{concept}/deploy/prod/kustomization.yaml"
    if not os.path.exists(kustomization_path):
        print(f"Error: {kustomization_path} not found. skipping {app}.")
        return

    with open(kustomization_path, 'r') as f:
        content = f.read()

    # Match: - name: .../app ... newTag: ...
    pattern = re.compile(rf"(-\s+name: .*?{app}.*?\n\s+newTag: ).*")
    
    if pattern.search(content):
        new_content = pattern.sub(rf"\g<1>{version}", content)
        if content != new_content:
            with open(kustomization_path, 'w') as f:
                f.write(new_content)
            print(f"Updated Kustomization {kustomization_path} for {app}")
    else:
        print(f"Warning: Could not find image entry for {app} in {kustomization_path}")

def main():
    parser = argparse.ArgumentParser(description="Promote app to Prod environment")
    parser.add_argument("--concept", required=True, help="Concept name (e.g. demo-concept)")
    parser.add_argument("--version", required=True, help="Version tag of the RELEASE (e.g. v1.0.0)")
    
    args = parser.parse_args()
    
    workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace_dir:
        os.chdir(workspace_dir)
        print(f"Running in workspace: {workspace_dir}")
        
    source_bom = f"releases/test/{args.concept}-{args.version}.yaml"
    
    print(f"Promoting Release {args.version} for {args.concept} from {source_bom}...")
    
    images = parse_bom_images(source_bom)
    if not images:
        print("Error: No images found in BOM.")
        sys.exit(1)
        
    # Update Prod BOM record
    update_prod_bom(args.concept, images)
    
    # Archive Prod BOM for rollback capability
    archived_bom = f"releases/prod/{args.concept}-{args.version}.yaml"
    import shutil
    shutil.copy(f"releases/prod/{args.concept}.yaml", archived_bom)
    print(f"Archived Prod BOM -> {archived_bom}")
    
    # Update Kustomization for each app in the BOM
    for app, tag in images.items():
        update_kustomization(args.concept, app, tag)
        
    # Automatically trigger manifest generation
    print("\nRefreshing ytt manifests...")
    os.system("bazelisk run //tools:gen_manifests")

if __name__ == "__main__":
    main()
