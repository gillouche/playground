#!/usr/bin/env bash
set -e

# Determines affected Bazel targets based on changed files since the last pushed commit.
# Outputs target lists that can be consumed by CI to run only what's needed.
#
# Usage:
#   affected_targets.sh [--base-commit <sha>]
#
# Output (to stdout):
#   AFFECTED_FULL_REBUILD=true|false
#   AFFECTED_BUILD_TARGETS=<space-separated targets or empty>
#   AFFECTED_UNIT_TARGETS=<space-separated targets or empty>
#   AFFECTED_LINT_TARGETS=<space-separated targets or empty>
#   AFFECTED_INTEGRATION_TARGETS=<space-separated targets or empty>

BASE_COMMIT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --base-commit)
            BASE_COMMIT="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Files that trigger a full rebuild when changed
FULL_REBUILD_PATTERNS=(
    "MODULE.bazel"
    "MODULE.bazel.lock"
    ".bazelrc"
    ".bazelversion"
    "tools/defs.bzl"
    "WORKSPACE"
    "WORKSPACE.bazel"
)

# Directories to ignore when determining affected targets
IGNORE_PATTERNS="^(\\.git|releases/|.*/deploy/)"

cd "$BUILD_WORKSPACE_DIRECTORY"

# Determine base commit if not provided
if [ -n "$BASE_COMMIT" ]; then
    echo "Using provided base commit: $BASE_COMMIT" >&2
else
    echo "Determining last pushed commit from Nexus..." >&2
    BASE_COMMIT=$(python3 tools/scripts/python/determine_base_commit.py)
    echo "Detected base commit: $BASE_COMMIT" >&2
fi

# Validate base commit exists locally
if ! git rev-parse --verify "$BASE_COMMIT" >/dev/null 2>&1; then
    echo "Warning: Base commit $BASE_COMMIT not found locally. Falling back to HEAD~1" >&2
    BASE_COMMIT="HEAD~1"
fi

echo "Analyzing changes between $BASE_COMMIT and HEAD..." >&2
echo "Base: $(git rev-parse --short "$BASE_COMMIT")" >&2
echo "Head: $(git rev-parse --short HEAD)" >&2

# Get all changed files
ALL_CHANGED_FILES=$(git diff --name-only "$BASE_COMMIT" HEAD 2>/dev/null || echo "")

if [ -z "$ALL_CHANGED_FILES" ]; then
    echo "No changes detected." >&2
    echo "AFFECTED_FULL_REBUILD=false"
    echo "AFFECTED_BUILD_TARGETS="
    echo "AFFECTED_UNIT_TARGETS="
    echo "AFFECTED_LINT_TARGETS="
    echo "AFFECTED_INTEGRATION_TARGETS="
    exit 0
fi

echo "Changed files:" >&2
echo "$ALL_CHANGED_FILES" | head -20 >&2
TOTAL_FILES=$(echo "$ALL_CHANGED_FILES" | wc -l | tr -d ' ')
if [ "$TOTAL_FILES" -gt 20 ]; then
    echo "... and $((TOTAL_FILES - 20)) more files" >&2
fi

# Check if any full-rebuild file changed
FULL_REBUILD=false
for pattern in "${FULL_REBUILD_PATTERNS[@]}"; do
    if echo "$ALL_CHANGED_FILES" | grep -qE "^${pattern}$"; then
        echo "Full rebuild triggered by: $pattern" >&2
        FULL_REBUILD=true
        break
    fi
done

if [ "$FULL_REBUILD" = true ]; then
    echo "AFFECTED_FULL_REBUILD=true"
    # For full rebuild, query all targets
    BUILD_TARGETS=$(bazel query '//...' 2>/dev/null | tr '\n' ' ')
    UNIT_TARGETS=$(bazel query 'attr(tags, unit, //...)' 2>/dev/null | tr '\n' ' ')
    LINT_TARGETS=$(bazel query 'attr(tags, lint, //...)' 2>/dev/null | tr '\n' ' ')
    INTEGRATION_TARGETS=$(bazel query 'attr(tags, integration, //...)' 2>/dev/null | tr '\n' ' ')

    echo "AFFECTED_BUILD_TARGETS=$BUILD_TARGETS"
    echo "AFFECTED_UNIT_TARGETS=$UNIT_TARGETS"
    echo "AFFECTED_LINT_TARGETS=$LINT_TARGETS"
    echo "AFFECTED_INTEGRATION_TARGETS=$INTEGRATION_TARGETS"
    exit 0
fi

echo "AFFECTED_FULL_REBUILD=false"

# Filter out ignored directories (deploy/, releases/, .git/)
RELEVANT_FILES=$(echo "$ALL_CHANGED_FILES" | grep -vE "$IGNORE_PATTERNS" || true)

if [ -z "$RELEVANT_FILES" ]; then
    echo "No relevant code changes (only deploy/releases/config files changed)." >&2
    echo "AFFECTED_BUILD_TARGETS="
    echo "AFFECTED_UNIT_TARGETS="
    echo "AFFECTED_LINT_TARGETS="
    echo "AFFECTED_INTEGRATION_TARGETS="
    exit 0
fi

# Convert to space-separated for Bazel set()
FILES_LIST=$(echo "$RELEVANT_FILES" | tr '\n' ' ')
echo "Relevant changed files for Bazel query: $FILES_LIST" >&2

# Query for affected targets
# rdeps(//..., set(files)) finds all targets that depend on the changed files
echo "Querying Bazel for affected targets..." >&2

# Build targets: all targets that depend on changed files
# Build targets: all targets that depend on changed files, EXCLUDING shell scripts and tools
BUILD_QUERY="rdeps(//..., set($FILES_LIST)) except kind(sh_binary, //...) except kind(sh_test, //...) except //tools/..."
BUILD_TARGETS=$(bazel query --keep_going "$BUILD_QUERY" 2>/dev/null | tr '\n' ' ' || echo "")

# Unit test targets: affected targets with 'unit' tag
UNIT_QUERY="attr(tags, unit, rdeps(//..., set($FILES_LIST)))"
UNIT_TARGETS=$(bazel query --keep_going "$UNIT_QUERY" 2>/dev/null | tr '\n' ' ' || echo "")

# Lint targets: affected targets with 'lint' tag
LINT_QUERY="attr(tags, lint, rdeps(//..., set($FILES_LIST)))"
LINT_TARGETS=$(bazel query --keep_going "$LINT_QUERY" 2>/dev/null | tr '\n' ' ' || echo "")

# Integration test targets: affected targets with 'integration' tag
INTEGRATION_QUERY="attr(tags, integration, rdeps(//..., set($FILES_LIST)))"
INTEGRATION_TARGETS=$(bazel query --keep_going "$INTEGRATION_QUERY" 2>/dev/null | tr '\n' ' ' || echo "")

echo "Found affected targets:" >&2
echo "  Build: $(echo "$BUILD_TARGETS" | wc -w | tr -d ' ') targets" >&2
echo "  Unit tests: $(echo "$UNIT_TARGETS" | wc -w | tr -d ' ') targets" >&2
echo "  Lint: $(echo "$LINT_TARGETS" | wc -w | tr -d ' ') targets" >&2
echo "  Integration: $(echo "$INTEGRATION_TARGETS" | wc -w | tr -d ' ') targets" >&2

echo "AFFECTED_BUILD_TARGETS=$BUILD_TARGETS"
echo "AFFECTED_UNIT_TARGETS=$UNIT_TARGETS"
echo "AFFECTED_LINT_TARGETS=$LINT_TARGETS"
echo "AFFECTED_INTEGRATION_TARGETS=$INTEGRATION_TARGETS"
