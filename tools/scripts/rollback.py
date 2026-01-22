#!/usr/bin/env python3

import argparse
import os
import re
import shutil
import sys

def parse_bom_images(path):
    """Parse BOM to extract app:tag pairs."""
    with open(path, 'r') as f:
        content = f.read()
    
    images = {}
    pattern = re.compile(r"  (\S+):\s*\n\s+tag: (\S+)")
    for match in pattern.finditer(content):
        images[match.group(1)] = match.group(2)
    
    return images

def update_kustomization(concept, env, images):
    """Update kustomization files for all apps with rollback versions."""
    for app, tag in images.items():
        kustomization_path = f"apps/{concept}/{app}/deploy/{env}/kustomization.yaml"
        
        if not os.path.exists(kustomization_path):
            print(f"Warning: {kustomization_path} not found")
            continue
        
        with open(kustomization_path, 'r') as f:
            content = f.read()
        
        # Update newTag
        pattern = re.compile(rf"(-\s+name: .*{app}.*?\n\s+newTag: ).*")
        
        if pattern.search(content):
            content = pattern.sub(rf"\1{tag}", content)
            with open(kustomization_path, 'w') as f:
                f.write(content)
            print(f"  Updated {app} kustomization -> {tag}")
        else:
            print(f"  Warning: Could not find image entry for {app}")

def rollback(env, concept, version):
    """Rollback environment to specific version."""
    if env not in ["test", "prod"]:
        print(f"Error: --env must be 'test' or 'prod', got '{env}'")
        sys.exit(1)
    
    archived_bom = f"releases/{env}/{concept}-{version}.yaml"
    head_bom = f"releases/{env}/{concept}.yaml"
    
    if not os.path.exists(archived_bom):
        print(f"Error: Archived BOM not found: {archived_bom}")
        print(f"Available versions:")
        # List available versions
        env_dir = f"releases/{env}"
        if os.path.exists(env_dir):
            for f in os.listdir(env_dir):
                if f.startswith(f"{concept}-") and f.endswith(".yaml"):
                    print(f"  - {f.replace(concept + '-', '').replace('.yaml', '')}")
        sys.exit(1)
    
    print(f"Rolling back {concept} in {env} to {version}...")
    
    # Copy archived BOM to HEAD
    shutil.copy(archived_bom, head_bom)
    print(f"  Copied {archived_bom} -> {head_bom}")
    
    # Update kustomization files
    images = parse_bom_images(head_bom)
    update_kustomization(concept, env, images)
    
    print(f"\nRollback complete! {concept} in {env} is now at {version}")
    print(f"Images:")
    for app, tag in images.items():
        print(f"  - {app}: {tag}")

def main():
    parser = argparse.ArgumentParser(description="Rollback Test or Prod environment to archived version")
    parser.add_argument("--env", required=True, choices=["test", "prod"], help="Environment to rollback (test/prod)")
    parser.add_argument("--concept", required=True, help="Concept name")
    parser.add_argument("--version", required=True, help="Version to rollback to (e.g., v1.0.0)")
    
    args = parser.parse_args()
    rollback(args.env, args.concept, args.version)

if __name__ == "__main__":
    main()
