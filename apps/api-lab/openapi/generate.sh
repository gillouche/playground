#!/usr/bin/env bash
# Generate server stubs from the OpenAPI spec for Python.
#
# Usage:
#   ./apps/api-lab/openapi/generate.sh          # Generate Python (default)
#   ./apps/api-lab/openapi/generate.sh python   # Generate Python explicitly
#
# Generated code provides:
#   - Pydantic v2 models matching the OpenAPI schemas
#   - The api_interface.py and __init__.py are maintained manually
#
# Generated code is committed to the repository.
# To regenerate after changing openapi.yaml:
#   1. Run this script
#   2. Review the diff
#   3. Update implementation code if interfaces changed
#   4. Commit the regenerated files

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPEC="$SCRIPT_DIR/openapi.yaml"
API_LAB_DIR="$(dirname "$SCRIPT_DIR")"

TARGET="${1:-python}"

echo "Generating from: $SPEC"

generate_python() {
    echo "==> Python: generating models and interface..."
    local out_dir="$API_LAB_DIR/python-common/src/generated"
    mkdir -p "$out_dir"

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

case "$TARGET" in
    python|all) generate_python ;;
    *)
        echo "Usage: $0 [python]"
        echo "(Only Python is currently supported; go/ts implementations are out of scope.)"
        exit 1
        ;;
esac

echo ""
echo "Generation complete. Review changes with: git diff apps/api-lab/python-common/src/generated/"
