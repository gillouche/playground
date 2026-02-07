#!/usr/bin/env python3
"""
Ruff lint runner for Bazel py_test targets.

This script runs ruff check on the source files passed as arguments.
It's used as the main entry point for py_test lint targets.
"""

import runpy
import sys

if __name__ == "__main__":
    # Set up argv for ruff - it expects 'ruff check ...' style arguments
    sys.argv = ["ruff", "check"] + sys.argv[1:]

    # Run ruff.__main__ using runpy (equivalent to python -m ruff)
    # This works because ruff is in the deps and its __main__.py handles execution
    runpy.run_module("ruff", run_name="__main__", alter_sys=True)
