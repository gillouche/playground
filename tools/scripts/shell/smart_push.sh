#!/usr/bin/env bash
set -e

BASE_COMMIT=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --tag) # consume --tag arguments passed to the underlying binary
            shift 2
            ;;
        -*)
            echo "Unknown option $1"
            shift
            ;;
        *)
            if [ -z "$BASE_COMMIT" ]; then
                BASE_COMMIT="$1"
            fi
            shift
            ;;
    esac
done

if [ -n "$BASE_COMMIT" ]; then
    echo "Using provided base commit: $BASE_COMMIT"
else
    echo "Determining last pushed commit from Nexus..."
    cd "$BUILD_WORKSPACE_DIRECTORY"
    BASE_COMMIT=$(python3 tools/scripts/python/determine_base_commit.py)
    echo "Detected base commit: $BASE_COMMIT"
fi

if ! git rev-parse --verify "$BASE_COMMIT" >/dev/null 2>&1; then
    echo "Warning: Base commit $BASE_COMMIT not found locally. Fallback to HEAD~1"
    BASE_COMMIT="HEAD~1"
fi

echo "Analyzing changes between $BASE_COMMIT and HEAD..."
git rev-parse --short "$BASE_COMMIT"
git rev-parse --short HEAD

CHANGED_FILES=$(git diff --name-only "$BASE_COMMIT" | grep -vE "^(\.git|releases|deploy)" || true)

if [ -z "$CHANGED_FILES" ]; then
    echo "No relevant code changes detected. Skipping image push."
    echo "SMART_PUSH_RESULT: image_pushed=false"
    exit 0
fi

FILES_LIST=$(echo "$CHANGED_FILES" | tr '\n' ' ')

echo "Changed files: $FILES_LIST"

QUERY="kind(oci_push, rdeps(//..., set($FILES_LIST)))"

echo "Querying Bazel for affected targets..."
TARGETS=$(bazelisk query --keep_going "$QUERY" 2>/dev/null || true)

if [ -z "$TARGETS" ]; then
    echo "No OCI push targets affected by these changes."
    echo "SMART_PUSH_RESULT: image_pushed=false"
    exit 0
fi

echo "Affected targets to push:"
echo "$TARGETS"

GIT_SHA=$(git rev-parse --short HEAD)
echo "Pushing images with tags: latest, $GIT_SHA"

for target in $TARGETS; do
    echo "Pushing $target..."
    bazelisk run "$target" -- --tag latest --tag "$GIT_SHA"
done

echo "SMART_PUSH_RESULT: image_pushed=true image_tag=$GIT_SHA"
