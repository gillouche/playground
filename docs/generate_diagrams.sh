#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIAGRAMS_DIR="${SCRIPT_DIR}/diagrams"
OUTPUT_DIR="${SCRIPT_DIR}/content/assets/diagrams"

mkdir -p "${OUTPUT_DIR}"

if ! command -v mmdc &>/dev/null; then
    echo "ERROR: mmdc not found. Enter the Nix dev shell (nix develop ./nix) to get mermaid-cli." >&2
    exit 1
fi

if [ -z "${PUPPETEER_EXECUTABLE_PATH:-}" ]; then
    if [ "$(uname)" = "Darwin" ]; then
        for chrome_path in \
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
            "/Applications/Chromium.app/Contents/MacOS/Chromium" \
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"; do
            if [ -x "${chrome_path}" ]; then
                export PUPPETEER_EXECUTABLE_PATH="${chrome_path}"
                break
            fi
        done
    elif command -v chromium &>/dev/null; then
        PUPPETEER_EXECUTABLE_PATH="$(command -v chromium)"
        export PUPPETEER_EXECUTABLE_PATH
    elif command -v google-chrome-stable &>/dev/null; then
        PUPPETEER_EXECUTABLE_PATH="$(command -v google-chrome-stable)"
        export PUPPETEER_EXECUTABLE_PATH
    fi
fi

if [ -z "${PUPPETEER_EXECUTABLE_PATH:-}" ]; then
    echo "ERROR: No Chrome/Chromium browser found. Install Chrome or set PUPPETEER_EXECUTABLE_PATH." >&2
    exit 1
fi

found=0
for mmd_file in "${DIAGRAMS_DIR}"/*.mmd; do
    [ -f "${mmd_file}" ] || continue
    found=1
    name="$(basename "${mmd_file}" .mmd)"
    output="${OUTPUT_DIR}/${name}.svg"
    echo "Rendering ${name}.mmd -> ${name}.svg"
    mmdc -i "${mmd_file}" -o "${output}" -b transparent --quiet
done

if [ "${found}" -eq 0 ]; then
    echo "WARNING: No .mmd files found in ${DIAGRAMS_DIR}" >&2
fi
