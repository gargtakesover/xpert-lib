"""Tests for xpert.config module."""

import pytest
from pathlib import Path

from xpert.config import (
    NITTER_INSTANCES, DEFAULT_LIMIT, ENGINE_DIR, SESSIONS_FILE,
    UA, REQUEST_TIMEOUT, CONFIG_DIR,
)


class TestConfigModule:
    """Tests for xpert.config module."""

    def test_nitter_instances_defined(self):
        """Nitter instances should be defined and accessible."""
        assert isinstance(NITTER_INSTANCES, list)
        assert len(NITTER_INSTANCES) >= 1
        assert all(isinstance(url, str) for url in NITTER_INSTANCES)
        # Should include localhost options
        assert any("localhost" in url for url in NITTER_INSTANCES)

    def test_default_limit_is_positive(self):
        """DEFAULT_LIMIT should be a positive integer."""
        assert isinstance(DEFAULT_LIMIT, int)
        assert DEFAULT_LIMIT > 0

    def test_engine_dir_is_path(self):
        """ENGINE_DIR should be a valid Path object."""
        assert isinstance(ENGINE_DIR, Path)

    def test_sessions_file_is_path(self):
        """SESSIONS_FILE should be a valid Path object."""
        assert isinstance(SESSIONS_FILE, Path)

    def test_user_agent_defined(self):
        """UA should be a non-empty string."""
        assert isinstance(UA, str)
        assert len(UA) > 0

    def test_request_timeout_is_positive(self):
        """REQUEST_TIMEOUT should be a positive float."""
        assert isinstance(REQUEST_TIMEOUT, (int, float))
        assert REQUEST_TIMEOUT > 0

    def test_config_dir_created(self):
        """CONFIG_DIR should exist or be creatable."""
        assert isinstance(CONFIG_DIR, Path)
