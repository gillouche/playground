#!/usr/bin/env python3
"""
Bandit security scanner runner for Bazel py_test targets.

This script runs bandit on the source files passed as arguments.
It's used as the main entry point for py_test security scan targets.

Produces JUnit XML output for Bazel to avoid the generate-xml.sh
segfault on macOS during Python C extension cleanup.
"""

import os
import sys

import runpy

if __name__ == "__main__":
    args = sys.argv[1:]

    # Produce JUnit XML for Bazel so it doesn't run generate-xml.sh
    # Also run text output so findings are visible in the test log
    xml_output = os.environ.get("XML_OUTPUT_FILE")
    if xml_output:
        # Write XML for Bazel, but also print text to stderr
        args = ["-f", "xml", "-o", xml_output] + args

    sys.argv = ["bandit"] + args
    try:
        runpy.run_module("bandit", run_name="__main__", alter_sys=True)
    except SystemExit as e:
        # If bandit found issues (exit 1), also run text format for visibility
        if e.code == 1 and xml_output:
            # Re-run with text output to stderr so user sees findings
            text_args = [a for a in args if a not in ("-f", "xml", "-o", xml_output)]
            sys.argv = ["bandit"] + text_args
            try:
                runpy.run_module("bandit", run_name="__main__", alter_sys=True)
            except SystemExit:
                pass
        raise
