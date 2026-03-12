#!/usr/bin/env bash
# Generate server stubs from OpenAPI spec for all languages.
#
# Usage:
#   ./apps/api-lab/openapi/generate.sh          # Generate all
#   ./apps/api-lab/openapi/generate.sh python    # Generate Python only
#   ./apps/api-lab/openapi/generate.sh go        # Generate Go only
#   ./apps/api-lab/openapi/generate.sh ts        # Generate TypeScript only
#
# The generated code provides:
#   - Models/types matching the OpenAPI schemas
#   - Abstract interfaces (Python ABC / Go interface / TS interface) for route handlers
#   - Route registration wiring (parses params, encodes responses, correct status codes)
#
# Developers implement the interface methods with business logic.
# Similar to Spring Boot's openapi-generator generating controller interfaces.
#
# Tools used:
#   Python:     datamodel-code-generator (Pydantic v2 models)
#   Go:         oapi-codegen (types + chi server interface)
#   TypeScript:  openapi-typescript (types)
#
# Currently, generated code is committed to the repository (not generated at build time).
# To regenerate after changing openapi.yaml:
#   1. Run this script
#   2. Review the diff
#   3. Update implementation code if interfaces changed
#   4. Commit the regenerated files

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPEC="$SCRIPT_DIR/openapi.yaml"
API_LAB_DIR="$(dirname "$SCRIPT_DIR")"

TARGET="${1:-all}"

echo "Generating from: $SPEC"

generate_python() {
    echo "==> Python: generating models and interface..."
    local out_dir="$API_LAB_DIR/python-common/src/generated"
    mkdir -p "$out_dir"

    # Generate Pydantic models from OpenAPI spec
    if command -v datamodel-codegen &>/dev/null; then
        datamodel-codegen \
            --input "$SPEC" \
            --input-file-type openapi \
            --output "$out_dir/models.py" \
            --output-model-type pydantic_v2.BaseModel \
            --target-python-version 3.14 \
            --use-union-operator \
            --field-constraints \
            --use-annotated \
            --enum-field-as-literal one \
            --use-standard-collections
        echo "    Generated $out_dir/models.py"
    else
        echo "    SKIP: datamodel-codegen not installed (pip install datamodel-code-generator)"
        echo "    Using hand-written models in $out_dir/models.py"
    fi

    echo "    Note: api_interface.py and __init__.py are maintained manually"
    echo "    Done."
}

generate_go() {
    echo "==> Go: generating types and server interface..."
    local out_dir="$API_LAB_DIR/go-api/generated"
    mkdir -p "$out_dir"

    if command -v oapi-codegen &>/dev/null; then
        # Generate types
        oapi-codegen \
            -generate types \
            -package generated \
            -o "$out_dir/models.go" \
            "$SPEC"
        echo "    Generated $out_dir/models.go"

        # Generate server interface (std http)
        oapi-codegen \
            -generate std-http-server \
            -package generated \
            -o "$out_dir/server.go" \
            "$SPEC"
        echo "    Generated $out_dir/server.go"
    else
        echo "    SKIP: oapi-codegen not installed (go install github.com/oapi-codegen/oapi-codegen/v2/cmd/oapi-codegen@latest)"
        echo "    Using hand-written types in $out_dir/"
    fi

    echo "    Done."
}

generate_ts() {
    echo "==> TypeScript: generating types and server interface..."
    local out_dir="$API_LAB_DIR/ts-api/src/generated"
    mkdir -p "$out_dir"

    if command -v npx &>/dev/null && npx openapi-typescript --help &>/dev/null 2>&1; then
        npx openapi-typescript "$SPEC" -o "$out_dir/models.ts"
        echo "    Generated $out_dir/models.ts"
    else
        echo "    SKIP: openapi-typescript not installed (npm install -D openapi-typescript)"
        echo "    Using hand-written types in $out_dir/"
    fi

    echo "    Note: server.ts and index.ts are maintained manually"
    echo "    Done."
}

case "$TARGET" in
    python) generate_python ;;
    go)     generate_go ;;
    ts)     generate_ts ;;
    all)
        generate_python
        generate_go
        generate_ts
        ;;
    *)
        echo "Usage: $0 [python|go|ts|all]"
        exit 1
        ;;
esac

echo ""
echo "Generation complete. Review changes with: git diff apps/api-lab/*/generated/"
