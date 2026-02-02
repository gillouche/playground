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
    
    # 3. Parse BOM to get images and metadata
    # Structure:
    # images:
    #   component:
    #     tag: ...
    #     commit: ...
    #     full_tag: ...
    
    images = {}
    with open(source_bom, 'r') as f:
        content = f.read()
        
    # Python-only parsing (no yaml dependency)
    # We iterate lines looking for components under 'images:'
    lines = content.splitlines()
    in_images_section = False
    current_component = None
    
    for line in lines:
        stripped = line.strip()
        if stripped == "images:":
            in_images_section = True
            continue
        
        if not in_images_section:
            continue
            
        # Check for indent 2 (component)
        if line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
            current_component = line.strip()[:-1]
            images[current_component] = {}
        
        # Check for indent 4 (attributes)
        elif current_component and line.startswith("    ") and not line.startswith("      "):
            if ":" in stripped:
                key, val = stripped.split(":", 1)
                val = val.strip()
                if val:
                    images[current_component][key.strip()] = val
        
        # Check for indent 6 (nested attributes, e.g. image.ref)
        elif current_component and line.startswith("      "):
            if ":" in stripped:
                key, val = stripped.split(":", 1)
                val = val.strip()
                # We specifically look for 'ref' which comes from 'image' block
                if key.strip() == "ref":
                     images[current_component]["image_ref"] = val

    if not images:
        print("Warning: No images found in BOM. Skipping updates.")
    else:
        update_kustomization(app, target_env, images)
        
        # 5. Regenerate Manifests (Target Env Only)
        print(f"Regenerating manifests for {target_env}...")
        
        for comp in images.keys():
             print(f"  Regenerating {comp} for {target_env}...")
             ret = os.system(f"bazel run //tools:gen_manifests -- {app} {comp} {target_env}")
             if ret != 0:
                 print(f"Error generating manifests for {comp}.")
                 sys.exit(1)
            
        # 6. Update ConfigMaps (Metadata) AFTER generation
        # because gen_manifests overwrites them from templates
        update_configmaps(app, target_env, version, images)
            
    print(f"\nSuccessfully promoted {app} {version} to {target_env}")

def update_configmaps(app_name, env, version, images):
    deploy_dir = f"apps/{app_name}/deploy/{env}"
    if not os.path.exists(deploy_dir):
        return

    for filename in os.listdir(deploy_dir):
        if filename.endswith("-configmap.yaml"):
            filepath = os.path.join(deploy_dir, filename)
            component = filename.replace("-configmap.yaml", "")
            
            if component in images:
                comp_data = images[component]
                print(f"Updating ConfigMap: {filepath}")
                
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                
                new_lines = []
                data_section = False
                
                # We expect simple key-value pairs in 'data:' section
                # If keys don't exist, we should append them? 
                # Better: Regex replace existing known keys.
                
                replacements = {
                    "APP_VERSION": version,
                    "GIT_TAG": comp_data.get("full_tag", "unknown"),
                    "GIT_COMMIT": comp_data.get("commit", "unknown"),
                    "APP": app_name,
                    "COMPONENT": component
                }
                
                for line in lines:
                    updated_line = line
                    for key, val in replacements.items():
                        # Match "  KEY: value" or "  KEY:"
                        if re.match(rf"\s+{key}:", line):
                             updated_line = re.sub(rf"(\s+{key}:).*", rf"\1 {val}", line)
                    new_lines.append(updated_line)
                
                with open(filepath, 'w') as f:
                    f.writelines(new_lines)

def update_kustomization(app_name, env, images):
    kustomization_path = f"apps/{app_name}/deploy/{env}/kustomization.yaml"
    
    if not os.path.exists(kustomization_path):
        print(f"Error: {kustomization_path} not found.")
        return

    with open(kustomization_path, 'r') as f:
        content = f.read()

    updated = False
    
    # Check for images section
    if "images:" not in content:
        # naive append if missing, though usually it exists
        if not content.endswith("\n"): content += "\n"
        content += "\nimages:\n"
        updated = True

    for comp, data in images.items():
        tag = data.get("tag")
        if not tag: continue
        
        # extract repo from image_ref or full_tag or hardcoded assumption
        # image_ref = "nexus.../name:tag" -> we want "nexus.../name"
        image_ref = data.get("image_ref")
        if image_ref and ":" in image_ref:
            repo_name = image_ref.rsplit(":", 1)[0]
        else:
             # Fallback if image_ref parsing failed (should not happen with new parser)
             print(f"  Warning: No image_ref found for {comp}, cannot add new entry safely.")
             continue

        # Kustomize pattern to match existing entry
        # - name: nexus.../demo-app/greeting-service
        #   newTag: ...
        # match strictly on the repo name
        pattern = re.compile(rf"(-\s+name: {re.escape(repo_name)}\s*\n\s+newTag: ).*")
        
        if pattern.search(content):
            new_content = pattern.sub(rf"\g<1>{tag}", content)
            if content != new_content:
                content = new_content
                updated = True
                print(f"  Updated {comp} image -> {tag}")
        else:
            print(f"  Adding missing image entry for {comp}...")
            # Append to images section
            # We assume 'images:' exists (ensured above)
            # Find the line "images:" and append after it? Or at the end of the block?
            # Kustomize doesn't strictly require order, but indentation matters.
            # Safe bet: append to the end of the `images:` list if possible, or just replace `images:` with `images:\n  - name...` 
            # But regex sub is cleaner if we just find `images:` and insert after.
            
            new_entry = f"  - name: {repo_name}\n    newTag: {tag}\n"
            content = content.replace("images:\n", f"images:\n{new_entry}")
            updated = True
            
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
