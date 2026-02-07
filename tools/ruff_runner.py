#!/usr/bin/env python3
"""
Ruff lint runner for Bazel py_test targets.

This script runs ruff check on the source files passed as arguments.
It's used as the main entry point for py_test lint targets.
"""

import subprocess
import sys


if __name__ == "__main__":
    # Run ruff check with any command-line arguments passed
    # Default to check mode (no --fix)
    args = ["ruff", "check"] + sys.argv[1:]
    result = subprocess.run(args)
    sys.exit(result.returncode)
