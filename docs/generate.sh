#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACTION="${1:-serve}"

echo "=== Generating diagrams ==="
"${SCRIPT_DIR}/generate_diagrams.sh"

echo "=== Generating API reference ==="
python "${SCRIPT_DIR}/generate_api_docs.py"

case "${ACTION}" in
    serve)
        echo "=== Starting Zensical dev server ==="
        cd "${SCRIPT_DIR}"
        zensical serve
        ;;
    build)
        echo "=== Building static site ==="
        cd "${SCRIPT_DIR}"
        zensical build
        echo "Site built to ${SCRIPT_DIR}/site/"
        ;;
    *)
        echo "Usage: $0 {serve|build}" >&2
        exit 1
        ;;
esac
