#!/usr/bin/env python3
"""
Ruff lint runner for Bazel py_test targets.

This script runs ruff check on the source files passed as arguments.
It's used as the main entry point for py_test lint targets.
"""

import subprocess
import sys


if __name__ == "__main__":
    # Run ruff as a Python module using the current interpreter
    # This avoids PATH issues in Bazel sandbox
    args = [sys.executable, "-m", "ruff", "check"] + sys.argv[1:]
    result = subprocess.run(args)
    sys.exit(result.returncode)
