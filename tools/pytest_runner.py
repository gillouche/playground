#!/usr/bin/env python3
"""
Pytest runner for Bazel py_test targets.

This script runs pytest on the test files passed as arguments.
It's used as the main entry point for py_test targets that need
to run multiple test files.
"""

import sys
import pytest

if __name__ == "__main__":
    # Run pytest with any command-line arguments passed
    sys.exit(pytest.main(sys.argv[1:]))
