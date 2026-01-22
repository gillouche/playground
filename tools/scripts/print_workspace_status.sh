#!/usr/bin/env bash

git_commit=$(git rev-parse HEAD)
echo "STABLE_GIT_COMMIT ${git_commit}"

git_short_commit=$(git rev-parse --short HEAD)
echo "STABLE_GIT_SHORT_COMMIT ${git_short_commit}"
