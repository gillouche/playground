#!/usr/bin/env bash
set -e

# Usage: notify_discord.sh [START|SUCCESS|FAILURE] [JOB_NAME] [DETAILS]

STATUS="${1:-INFO}"
JOB_NAME="${2:-CI Job}"
DETAILS="${3:-No details provided.}"
WEBHOOK_URL="${DISCORD_WEBHOOK_URL:-}"

if [ -z "$WEBHOOK_URL" ]; then
    echo "DISCORD_WEBHOOK_URL not set. Skipping notification."
    exit 0
fi

# Define colors and titles based on status
case "$STATUS" in
    START)
        COLOR=3447003 # Blue
        TITLE="Build Started: $JOB_NAME"
        ;;
    SUCCESS)
        COLOR=3066993 # Green
        TITLE="Build Succeeded: $JOB_NAME"
        ;;
    FAILURE)
        COLOR=15158332 # Red
        TITLE="Build Failed: $JOB_NAME"
        ;;
    *)
        COLOR=10181046 # Gray
        TITLE="Build Status: $JOB_NAME"
        ;;
esac

# Get Git Info
COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "N/A")
COMMIT_MSG=$(git log -1 --pretty=%B 2>/dev/null | head -n 1 || echo "N/A")
REPO_URL="https://github.com/gillouche/playground"
RUN_URL="${REPO_URL}/actions/runs/${GITHUB_RUN_ID:-0}"

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
