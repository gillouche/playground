#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROTO_DIR="${SCRIPT_DIR}"
OUT_DIR="${SCRIPT_DIR}/../../python-grpc-api/src/generated"

mkdir -p "${OUT_DIR}"

python -m grpc_tools.protoc \
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
