"""Pytest configuration and fixtures."""
import os
import pytest

# Enable live tests only if RUN_LIVE_TESTS=1
def pytest_configure(config):
    config.addinivalue_line("markers", "integration: integration test against real Nitter")
    config.addinivalue_line("markers", "slow: slow running test")

@pytest.fixture
def allow_live_tests():
    return os.environ.get("RUN_LIVE_TESTS", "0") == "1"
