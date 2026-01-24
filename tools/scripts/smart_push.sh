#!/bin/bash
set -euo pipefail

PUSH_CMD="$1"

# Resolve the executable path relative to the workspace root
# Bazel runfiles handling
if [[ ! "$PUSH_CMD" = /* ]]; then
  # pass the "location" of the target.
  :
fi

GIT_TAG="git-$(git rev-parse --short HEAD)"

echo "Pushing image with tags: latest, $GIT_TAG"

# Run the oci_push command with runtime flags
# Note: rules_oci oci_push accepts flags passed after --
shift
echo "Delegating to oci_push with args: $@"
"$PUSH_CMD" --tag latest --tag "$GIT_TAG" "$@"
