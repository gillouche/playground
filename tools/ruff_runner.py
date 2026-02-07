#!/usr/bin/env python3
"""
Ruff lint runner for Bazel py_test targets.

This script runs ruff check on the source files passed as arguments.
It's used as the main entry point for py_test lint targets.
"""

import sys

# Import ruff's main module directly to avoid PATH issues in Bazel sandbox
from ruff.__main__ import main as ruff_main


if __name__ == "__main__":
    # Construct args for ruff check
    # sys.argv[0] is this script, replace it with 'ruff' and add 'check' command
    sys.argv = ["ruff", "check"] + sys.argv[1:]
    ruff_main()
