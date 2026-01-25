#!/bin/bash
set -e

PKG_DIR=${1:-"."}
THRESHOLD=80

echo "Running Go tests with coverage in $PKG_DIR..."

 cd "$PKG_DIR"

go test -coverprofile=coverage.out ./...

COVERAGE=$(go tool cover -func=coverage.out | grep total | awk '{print $3}' | tr -d '%')

echo "Total Scope Coverage: ${COVERAGE}%"

IS_PASS=$(python3 -c "print(1 if $COVERAGE >= $THRESHOLD else 0)")

if [ "$IS_PASS" -eq 1 ]; then
    echo "PASS: Coverage ${COVERAGE}% >= ${THRESHOLD}%"
    rm coverage.out
    exit 0
else
    echo "FAIL: Coverage ${COVERAGE}% < ${THRESHOLD}%"
    rm coverage.out
    exit 1
fi
