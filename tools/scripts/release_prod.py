#!/usr/bin/env python3

import argparse
import os
import shutil
import sys

def archive_bom(concept, version):
    source = f"releases/prod/{concept}.yaml"
    dest = f"releases/prod/{concept}-{version}.yaml"
    
    if not os.path.exists(source):
        print(f"Error: Source BOM {source} does not exist.")
        sys.exit(1)
        
    if os.path.exists(dest):
        print(f"Warning: Destination BOM {dest} already exists. Overwriting.")
    
    shutil.copy2(source, dest)
    print(f"Archived BOM: {source} -> {dest}")

def main():
    parser = argparse.ArgumentParser(description="Archive Prod BOM to a versioned release")
    parser.add_argument("--concept", required=True, help="Concept name (e.g. demo-concept)")
    parser.add_argument("--version", required=True, help="Version tag (e.g. v1.0.0)")
    
    args, _ = parser.parse_known_args()
    
    workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace_dir:
        os.chdir(workspace_dir)
        print(f"Running in workspace: {workspace_dir}")
        
    archive_bom(args.concept, args.version)

if __name__ == "__main__":
    main()
