#!/usr/bin/env python3
"""
Pytest runner for Bazel py_test targets.

This script runs pytest on the test files passed as arguments.
It's used as the main entry point for py_test targets that need
to run multiple test files.
"""

import os
import sys
import pytest

if __name__ == "__main__":
    args = sys.argv[1:]
    # Produce JUnit XML for Bazel so it doesn't run generate-xml.sh
    # (which can segfault on macOS during Python C extension cleanup)
    xml_output = os.environ.get("XML_OUTPUT_FILE")
    if xml_output:
        args = [f"--junitxml={xml_output}"] + args
    sys.exit(pytest.main(args))
