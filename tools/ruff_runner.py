#!/usr/bin/env python3
"""
Ruff lint runner for Bazel py_test targets.

This script runs ruff check on the source files passed as arguments.
It's used as the main entry point for py_test lint targets.

Uses subprocess to invoke the ruff binary directly, since the ruff
Python wrapper's binary discovery doesn't work in Bazel's sandbox.

Produces JUnit XML output for Bazel to avoid the generate-xml.sh
segfault on macOS during Python C extension cleanup.
"""

import os
import subprocess
import sys
import xml.etree.ElementTree as ET


def _find_ruff_binary():
    """Find the ruff binary in Bazel runfiles."""
    runfiles = os.environ.get("RUNFILES_DIR", "")
    if not runfiles:
        return None

    # The ruff :data target puts the binary in the runfiles tree
    # Walk the runfiles looking for bin/ruff
    for dirpath, dirnames, filenames in os.walk(runfiles):
        if "ruff" in filenames:
            candidate = os.path.join(dirpath, "ruff")
            # Skip Python files, we want the actual binary
            if (
                os.access(candidate, os.X_OK)
                and not candidate.endswith(".py")
                and "site-packages" not in dirpath
                and os.path.basename(dirpath) == "bin"
            ):
                return candidate
        # Limit depth to avoid excessive walking
        depth = dirpath.count(os.sep) - runfiles.count(os.sep)
        if depth > 6:
            dirnames.clear()

    return None


def _write_junit_xml(xml_path, returncode, output):
    """Write JUnit XML so Bazel doesn't run generate-xml.sh."""
    testsuite = ET.Element(
        "testsuite",
        name="ruff",
        tests="1",
        failures=str(1 if returncode else 0),
    )
    testcase = ET.SubElement(testsuite, "testcase", name="ruff-check")
    if returncode:
        failure = ET.SubElement(testcase, "failure", message="ruff check failed")
        failure.text = output
    tree = ET.ElementTree(testsuite)
    tree.write(xml_path, xml_declaration=True, encoding="unicode")


if __name__ == "__main__":
    ruff_bin = _find_ruff_binary()
    args = sys.argv[1:]
    xml_output = os.environ.get("XML_OUTPUT_FILE")

    if ruff_bin:
        result = subprocess.run(
            [ruff_bin, "check"] + args,
            capture_output=True,
            text=True,
        )
        output = (result.stdout or "") + (result.stderr or "")
        if output:
            print(output, file=sys.stderr)
        if xml_output:
            _write_junit_xml(xml_output, result.returncode, output)
        sys.exit(result.returncode)
    else:
        msg = "ERROR: Could not find ruff binary in runfiles"
        print(msg, file=sys.stderr)
        if xml_output:
            _write_junit_xml(xml_output, 1, msg)
        sys.exit(1)
