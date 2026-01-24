#!/usr/bin/env python3

import argparse
import os
import shutil
import sys

def freeze_concept(concept, version):
    """
    Freeze the current Dev BOM for a concept into a versioned release.
    Source: releases/dev/{concept}.yaml
    Dest:   releases/dev/{concept}-{version}.yaml
    """
    source_path = f"releases/dev/{concept}.yaml"
    dest_path = f"releases/dev/{concept}-{version}.yaml"

    if not os.path.exists(source_path):
        print(f"Error: Source Dev BOM {source_path} does not exist.")
        print("Please run //tools:sync_dev first.")
        sys.exit(1)

    if os.path.exists(dest_path):
        print(f"Warning: Destination BOM {dest_path} already exists. Overwriting.")

    # Read source content
    with open(source_path, 'r') as f:
        content = f.read()

    # Prepend metadata
    metadata = f"metadata:\n  concept: {concept}\n  version: {version}\n"
    new_content = metadata + content

    # Write versioned BOM
    with open(dest_path, 'w') as f:
        f.write(new_content)
        
    print(f"Successfully frozen {concept} {version}")
    print(f"Created: {dest_path}")

def main():
    parser = argparse.ArgumentParser(description="Freeze current Dev state into a versioned BOM")
    parser.add_argument("--concept", required=True, help="Concept name (e.g. demo-concept)")
    parser.add_argument("--version", required=True, help="Version tag (e.g. v1.0.0)")

    args = parser.parse_args()

    # Bazel workspace handling
    workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace_dir:
        os.chdir(workspace_dir)

    freeze_concept(args.concept, args.version)

if __name__ == "__main__":
    main()
