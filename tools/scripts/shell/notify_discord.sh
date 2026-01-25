#!/usr/bin/env bash
set -e

# Usage: notify_discord.sh [START|SUCCESS|FAILURE] [JOB_NAME] [DETAILS]
#
# Environment variables for release notifications:
#   RELEASE_CONCEPT - concept name
#   RELEASE_APP - app name
#   RELEASE_VERSION - version
#   RELEASE_TAG - full release tag
#   RELEASE_IMAGE_TAG - created image tag

STATUS="${1:-INFO}"
JOB_NAME="${2:-CI Job}"
DETAILS="${3:-No details provided.}"
WEBHOOK_URL="${DISCORD_WEBHOOK_URL:-}"

if [ -z "$WEBHOOK_URL" ]; then
    echo "DISCORD_WEBHOOK_URL not set. Skipping notification."
    exit 0
fi

# Define colors and titles based on status
# Determine action verb based on context
ACTION_VERB="Build"
if [ -n "$RELEASE_TAG" ] || [ -n "$RELEASE_CONCEPT" ]; then
    ACTION_VERB="Release"
fi

case "$STATUS" in
    START)
        COLOR=3447003 # Blue
        TITLE="$ACTION_VERB Started: $JOB_NAME"
        ;;
    SUCCESS)
        COLOR=3066993 # Green
        TITLE="$ACTION_VERB Succeeded: $JOB_NAME"
        ;;
    FAILURE)
        COLOR=15158332 # Red
        TITLE="$ACTION_VERB Failed: $JOB_NAME"
        ;;
    CRITICAL)
        COLOR=15158332 # Red
        TITLE="Fork on hosted runner: $JOB_NAME"
        ;;
    *)
        COLOR=10181046 # Gray
        TITLE="$ACTION_VERB Status: $JOB_NAME"
        ;;
esac

# Get Git Info
COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "N/A")
COMMIT_MSG=$(git log -1 --pretty=%B 2>/dev/null | head -n 1 || echo "N/A")
REPO_URL="https://github.com/gillouche/playground"
RUN_URL="${REPO_URL}/actions/runs/${GITHUB_RUN_ID:-0}"

# Build fields array based on notification type
if [ -n "$RELEASE_CONCEPT" ]; then
    # Release notification - show release-specific fields
    FIELDS=$(cat <<EOF
        {
          "name": "Concept",
          "value": "$RELEASE_CONCEPT",
          "inline": true
        },
        {
          "name": "App",
          "value": "$RELEASE_APP",
          "inline": true
        },
        {
          "name": "Version",
          "value": "$RELEASE_VERSION",
          "inline": true
        },
        {
          "name": "Tag",
          "value": "\`$RELEASE_TAG\`",
          "inline": true
        },
        {
          "name": "Commit",
          "value": "[\`$COMMIT_SHA\`]($REPO_URL/commit/$COMMIT_SHA)",
          "inline": true
        }
EOF
)
    # Add image tag field if provided
    if [ -n "$RELEASE_IMAGE_TAG" ]; then
        FIELDS="$FIELDS,"
        FIELDS="$FIELDS"$(cat <<EOF

        {
          "name": "Image Tag",
          "value": "\`$RELEASE_IMAGE_TAG\`",
          "inline": true
        }
EOF
)
    fi
else
    # Standard CI notification
    FIELDS=$(cat <<EOF
        {
          "name": "Commit",
          "value": "[\`$COMMIT_SHA\`]($REPO_URL/commit/$COMMIT_SHA)",
          "inline": true
        },
        {
          "name": "Message",
          "value": "$COMMIT_MSG",
          "inline": true
        },
        {
          "name": "Branch",
          "value": "${GITHUB_REF_NAME:-unknown}",
          "inline": true
        }
EOF
)
fi

# Build JSON Payload
PAYLOAD=$(cat <<EOF
{
  "embeds": [
    {
      "title": "$TITLE",
      "description": "$DETAILS",
      "url": "$RUN_URL",
      "color": $COLOR,
      "fields": [
$FIELDS
      ],
      "footer": {
        "text": "GitHub Actions • $JOB_NAME"
      },
      "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    }
  ]
}
EOF
)

# Send to Discord
curl -s -H "Content-Type: application/json" -d "$PAYLOAD" "$WEBHOOK_URL"
