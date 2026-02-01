#!/bin/bash
set -e

# Generic ytt manifest generator for the monorepo
# Usage: ./ytt_gen.sh [concept] [app] [env]

ROOT_DIR=$(git rev-parse --show-toplevel)
APPS_DIR="$ROOT_DIR/apps"

GENERATE_ALL=false
if [ "$#" -eq 0 ]; then
    GENERATE_ALL=true
fi

generate_app_env() {
    local concept=$1
    local app=$2
    local env=$3
    
    local base_dir="$APPS_DIR/$concept/$app/deploy/templates"
    local output_dir="$APPS_DIR/$concept/deploy/$env"
    
    if [ ! -d "$base_dir" ]; then
        return
    fi
    
    local cmd="ytt"
    
    # Read version info from release BOM using grep/awk (no external tools needed)
    local bom_file="$ROOT_DIR/releases/$env/$concept.yaml"
    local APP_VERSION="unknown"
    local COMPONENT_VERSION="unknown"
    local GIT_COMMIT="unknown"
    local GIT_TAG="unknown"
    
    if [ -f "$bom_file" ]; then
        # Parse YAML - extract metadata.version for APP_VERSION
        # and component-specific tag/commit/full_tag
        # BOM structure:
        #   metadata:
        #     version: dev | v0.0.7
        #   images:
        #     component-name:
        #       tag: v0.0.1
        #       commit: abc123...
        #       full_tag: app/component/v0.0.1
        
        local in_metadata=false
        local in_component=false
        
        while IFS= read -r line; do
            # Check for metadata section
            if [[ "$line" == "metadata:" ]]; then
                in_metadata=true
                in_component=false
                continue
            fi
            
            # Check for images section (exits metadata)
            if [[ "$line" == "images:" ]]; then
                in_metadata=false
                continue
            fi
            
            # Extract metadata.version
            if [ "$in_metadata" = true ]; then
                if [[ "$line" =~ ^"  version: " ]]; then
                    APP_VERSION="${line#*: }"
                fi
            fi
            
            # Check if we're entering the component section (2-space indent + component name + colon)
            if [[ "$line" =~ ^"  $app:" ]]; then
                in_component=true
                in_metadata=false
                continue
            fi
            
            # If in component, check for 4-space indent attributes
            if [ "$in_component" = true ]; then
                # Exit if we hit another component (2-space indent) or end
                if [[ "$line" =~ ^"  "[a-zA-Z] ]] && [[ ! "$line" =~ ^"    " ]]; then
                    break
                fi
                
                # Extract tag as COMPONENT_VERSION
                if [[ "$line" =~ ^"    tag: " ]]; then
                    COMPONENT_VERSION="${line#*: }"
                fi
                # Extract commit
                if [[ "$line" =~ ^"    commit: " ]]; then
                    GIT_COMMIT="${line#*: }"
                fi
                # Extract full_tag
                if [[ "$line" =~ ^"    full_tag: " ]]; then
                    GIT_TAG="${line#*: }"
                fi
            fi
        done < "$bom_file"
        
        # Fallback for missing values
        if [ "$GIT_COMMIT" = "unknown" ] || [ -z "$GIT_COMMIT" ]; then
            GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
        fi
        if [ -z "$GIT_TAG" ] || [ "$GIT_TAG" = "unknown" ]; then
            GIT_TAG="$COMPONENT_VERSION"
        fi
    fi

    # Find all ytt templates in the app's base deploy directory
    find "$base_dir" -name "*.ytt.yaml" | while read -r template; do
        filename=$(basename "$template" .ytt.yaml)
        output_file="$output_dir/${app}-${filename}.yaml"
        
        echo "Generating $output_file..."
        
        # Run ytt with context
        $cmd -f "$template" \
            -f "$base_dir/values.yaml" \
            -v component="$app" \
            -v app="$concept" \
            -v env="$env" \
            -v git_tag="$GIT_TAG" \
            -v git_commit="$GIT_COMMIT" \
            -v app_version="$APP_VERSION" \
            -v component_version="$COMPONENT_VERSION" \
            > "$output_file"
    done
}

if [ "$GENERATE_ALL" = true ]; then
    # Discover all concepts
    for concept_dir in "$APPS_DIR"/*/; do
        concept=$(basename "$concept_dir")
        
        # Discover all apps in this concept
        for app_dir in "$concept_dir"/*/; do
            app=$(basename "$app_dir")
            
            # Skip the 'deploy' directory at the concept level
            if [ "$app" == "deploy" ]; then
                continue
            fi
            
            # Generate for each environment
            for env in dev test prod; do
                generate_app_env "$concept" "$app" "$env"
            done
        done
    done
else
    # Generate for specific target
    generate_app_env "$1" "$2" "$3"
fi
