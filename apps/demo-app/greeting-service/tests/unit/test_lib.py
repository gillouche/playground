import os
from unittest import mock
from lib import get_greeting, sanitize

def test_get_greeting_default():
    # Test with no env var set (default)
    with mock.patch.dict(os.environ, {}, clear=True):
        result = get_greeting("Tester")
        assert result == "Hello, Tester! Welcome to the Playground (unknown)."

def test_get_greeting_with_env():
    # Test with specific env var
    with mock.patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        result = get_greeting("Tester")
        assert result == "Hello, Tester! Welcome to the Playground (production)."

def test_sanitize():
    assert sanitize(" clean ") == "clean"
    assert sanitize("<tag>") == "&lt;tag&gt;"
    assert sanitize(None) == ""
