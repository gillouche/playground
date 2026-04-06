#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROTO_DIR="${SCRIPT_DIR}"
OUT_DIR="${SCRIPT_DIR}/../../python-grpc-api/src/generated"
REQS_LOCK="${SCRIPT_DIR}/../../requirements_lock.txt"

GRPCIO_TOOLS_VERSION=$(grep "^grpcio-tools==" "$REQS_LOCK" | sed 's/grpcio-tools==\([^ \\]*\).*/\1/')
if [ -z "$GRPCIO_TOOLS_VERSION" ]; then
    echo "ERROR: Could not determine grpcio-tools version from $REQS_LOCK"
    exit 1
fi

echo "Using grpcio-tools==${GRPCIO_TOOLS_VERSION} (from requirements_lock.txt)"

VENV_DIR=$(mktemp -d)
trap 'rm -rf "$VENV_DIR"' EXIT

uv venv "$VENV_DIR" --python 3.14 -q
uv pip install --python "$VENV_DIR" "grpcio-tools==${GRPCIO_TOOLS_VERSION}" "protobuf" -q

mkdir -p "${OUT_DIR}"

"${VENV_DIR}/bin/python" -m grpc_tools.protoc \
    -I "${PROTO_DIR}" \
    --python_out="${OUT_DIR}" \
    --grpc_python_out="${OUT_DIR}" \
    --pyi_out="${OUT_DIR}" \
    "library/v1/library.proto"

touch "${OUT_DIR}/__init__.py"
mkdir -p "${OUT_DIR}/library/v1"
touch "${OUT_DIR}/library/__init__.py"
touch "${OUT_DIR}/library/v1/__init__.py"

echo "Generated Python gRPC stubs in ${OUT_DIR}"
