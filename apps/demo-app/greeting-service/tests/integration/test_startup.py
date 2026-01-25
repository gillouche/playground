
import os
import logging
from unittest import mock
from fastapi.testclient import TestClient
from main import app

def test_startup_logs(caplog):
    # Setup - mock environment
    env_vars = {
        "ENVIRONMENT": "unit-test",
        "HOSTNAME": "test-host-123",
        "LOG_LEVEL": "DEBUG"
    }
    
    with mock.patch.dict(os.environ, env_vars):
        # Trigger startup via TestClient context manager
        # Capture logs MUST allow startup to happen inside
        with caplog.at_level(logging.DEBUG, logger="demo-app"):
            with TestClient(app):
                pass
                
        # Assertions
        # Check if Environment was logged securely (not full environ)
        assert "Environment: unit-test" in caplog.text
        # Check if Hostname was logged at debug
        assert "Hostname: test-host-123" in caplog.text
        # Check standard info logs
        assert "Demo App Application Starting..." in caplog.text
        assert "Python Version:" in caplog.text

def test_startup_unknown_env(caplog):
     with caplog.at_level(logging.INFO, logger="demo-app"):
         with TestClient(app):
             pass
             
     assert "Environment: unknown" in caplog.text
