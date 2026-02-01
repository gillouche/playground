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
