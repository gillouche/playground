#!/bin/bash
set -e

# Generic ytt manifest generator for the monorepo
# Usage: ./ytt_gen.sh --env ENV [app] [component]
#
# Examples:
#   ./ytt_gen.sh --env dev                              # All apps, all components, dev only
#   ./ytt_gen.sh --env dev demo-app                     # All components of demo-app, dev only
#   ./ytt_gen.sh --env dev demo-app greeting-service    # Specific component, dev only

ROOT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")
if [ ! -d "$ROOT_DIR/releases" ] && [ -d "./releases" ]; then
    ROOT_DIR="."
fi
APPS_DIR="$ROOT_DIR/apps"

# Parse --env flag (required)
ENV_FILTER=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENV_FILTER="$2"
            shift 2
            ;;
        -*)
            echo "Unknown option: $1"
            echo "Usage: ./ytt_gen.sh --env ENV [app] [component]"
            exit 1
            ;;
        *)
            break
            ;;
    esac
done

# Validate --env is provided
if [ -z "$ENV_FILTER" ]; then
    echo "Error: --env is required"
    echo "Usage: ./ytt_gen.sh --env ENV [app] [component]"
    echo ""
    echo "Valid environments: sandbox, dev, test, prod"
    exit 1
fi

# Validate environment value
case "$ENV_FILTER" in
    sandbox|dev|test|prod)
        ;;
    *)
        echo "Error: Invalid environment '$ENV_FILTER'"
        echo "Valid environments: sandbox, dev, test, prod"
        exit 1
        ;;
esac

ENVS=("$ENV_FILTER")

GENERATE_ALL=false
if [ "$#" -eq 0 ]; then
    GENERATE_ALL=true
fi

generate_component_env() {
    local app=$1
    local component=$2
    local env=$3

    local base_dir="$APPS_DIR/$app/$component/deploy/templates"
    local output_dir="$APPS_DIR/$app/deploy/$env"

    # For sandbox, output to component subdirectory
    if [ "$env" = "sandbox" ]; then
        output_dir="$APPS_DIR/$app/deploy/sandbox/$component"
    fi

    if [ ! -d "$base_dir" ]; then
        return
    fi

    local cmd="ytt"

    # Read version info from release BOM using grep/awk (no external tools needed)
    local bom_file="$ROOT_DIR/releases/$env/$app.yaml"
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
                    # Strip YAML quotes
                    APP_VERSION="${APP_VERSION#\'}"
                    APP_VERSION="${APP_VERSION%\'}"
                    APP_VERSION="${APP_VERSION#\"}"
                    APP_VERSION="${APP_VERSION%\"}"
                fi
            fi

            # Check if we're entering the component section (2-space indent + component name + colon)
            if [[ "$line" =~ ^"  $component:" ]]; then
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
                    # Strip YAML quotes (e.g. '2269718' -> 2269718)
                    COMPONENT_VERSION="${COMPONENT_VERSION#\'}"
                    COMPONENT_VERSION="${COMPONENT_VERSION%\'}"
                    COMPONENT_VERSION="${COMPONENT_VERSION#\"}"
                    COMPONENT_VERSION="${COMPONENT_VERSION%\"}"
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

        if [ -z "$GIT_TAG" ] || [ "$GIT_TAG" = "unknown" ]; then
            echo "Component $component not found in BOM for $env. Skipping."
            return
        fi
    fi

    # Ensure output directory exists [FIX]
    mkdir -p "$output_dir"

    # Find all ytt templates in the app's base deploy directory
    find "$base_dir" -name "*.ytt.yaml" | while read -r template; do
        filename=$(basename "$template" .ytt.yaml)
        output_file="$output_dir/${component}-${filename}.yaml"

        echo "Generating $output_file..."

        # Run ytt with context
        $cmd -f "$template" \
            --data-values-file "$base_dir/values.yaml" \
            -v component="$component" \
            -v app="$app" \
            -v env="$env" \
            -v git_tag="$GIT_TAG" \
            -v git_commit="$GIT_COMMIT" \
            -v app_version="$APP_VERSION" \
            -v component_version="$COMPONENT_VERSION" \
            > "$output_file"

        # Remove empty files (e.g. conditionally skipped templates)
        if [ ! -s "$output_file" ] || ! grep -q "[^[:space:]]" "$output_file"; then
            echo "Removing empty file $output_file"
            rm "$output_file"
        fi
    done
}

if [ "$GENERATE_ALL" = true ]; then
    # Discover all apps
    for app_dir in "$APPS_DIR"/*/; do
        app=$(basename "$app_dir")

        # Discover all components in this app
        for component_dir in "$app_dir"/*/; do
            component=$(basename "$component_dir")

            # Skip the 'deploy' directory at the app level
            if [ "$component" == "deploy" ]; then
                continue
            fi

            # Generate for each environment
            for env in "${ENVS[@]}"; do
                generate_component_env "$app" "$component" "$env"
            done
        done
    done
elif [ "$#" -eq 1 ]; then
    # Generate for specific app (all components, filtered envs)
    app="$1"
    app_dir="$APPS_DIR/$app"

    if [ ! -d "$app_dir" ]; then
        echo "Error: App directory not found: $app_dir"
        exit 1
    fi

    # Discover all components in this app
    for component_dir in "$app_dir"/*/; do
        component=$(basename "$component_dir")

        # Skip the 'deploy' directory at the app level
        if [ "$component" == "deploy" ]; then
            continue
        fi

        # Generate for each environment
        for env in "${ENVS[@]}"; do
            generate_component_env "$app" "$component" "$env"
        done
    done
elif [ "$#" -eq 2 ]; then
    # Generate for specific app and component (filtered envs)
    app="$1"
    component="$2"

    for env in "${ENVS[@]}"; do
        generate_component_env "$app" "$component" "$env"
    done
else
    echo "Error: Too many arguments"
    echo "Usage: ./ytt_gen.sh [--env ENV] [app] [component]"
    exit 1
fi
