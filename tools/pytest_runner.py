#!/usr/bin/env python3

import os
import sys

import pytest

if __name__ == "__main__":
    args = sys.argv[1:]
    xml_output = os.environ.get("XML_OUTPUT_FILE")
    if xml_output:
        args = [f"--junitxml={xml_output}", *args]
    sys.exit(pytest.main(args))
