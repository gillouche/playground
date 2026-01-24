#!/usr/bin/env bash
set -e

BASE_COMMIT=${1:-HEAD~1}

if ! git rev-parse --verify "$BASE_COMMIT" >/dev/null 2>&1; then
    echo "Error: Base commit $BASE_COMMIT not found."
    exit 1
fi

echo "Analyzing changes between $BASE_COMMIT and HEAD..."
git rev-parse --short "$BASE_COMMIT"
git rev-parse --short HEAD

CHANGED_FILES=$(git diff --name-only "$BASE_COMMIT" | grep -vE "^(\.git|releases|deploy)" || true)

if [ -z "$CHANGED_FILES" ]; then
    echo "No relevant code changes detected. Skipping image push."
    exit 0
fi

FILES_LIST=$(echo "$CHANGED_FILES" | tr '\n' ' ')

echo "Changed files: $FILES_LIST"

QUERY="kind(oci_push, rdeps(//..., set($FILES_LIST)))"

echo "Querying Bazel for affected targets..."
TARGETS=$(bazelisk query "$QUERY" 2>/dev/null || true)

if [ -z "$TARGETS" ]; then
    echo "No OCI push targets affected by these changes."
    exit 0
fi

echo "Affected targets to push:"
echo "$TARGETS"

GIT_SHA=$(git rev-parse --short HEAD)
echo "Pushing images with tags: latest, git-$GIT_SHA"

for target in $TARGETS; do
    echo "Pushing $target..."
    bazelisk run "$target" -- --tag latest --tag "git-$GIT_SHA"
done
