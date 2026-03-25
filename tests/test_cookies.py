"""Tests for cookie/session management."""

import pytest
import tempfile
import os
from pathlib import Path

from xpert.cookies import (
    save_cookies, load_cookies, clear_cookies, has_cookies,
    validate_cookies, get_cookies_status, CookieError,
)


class TestValidateCookies:
    def test_valid_cookies(self):
        valid, msg = validate_cookies(
            "abcdef123456abcdef123456abcdef123456",
            "123456abcdef123456abcdef123456abcdef",
        )
        assert valid is True

    def test_token_too_short(self):
        valid, msg = validate_cookies("abc", "ct0value12345678901234567890")
        assert valid is False

    def test_ct0_too_short(self):
        valid, msg = validate_cookies("token123456789012345678901234", "abc")
        assert valid is False

    def test_non_hex_token(self):
        valid, msg = validate_cookies("ghijklmnopqrstuvwxyz1234567890ab", "ct012345678901234567890123456ab")
        assert valid is False


class TestSaveLoadCookies:
    def test_save_and_load(self, tmp_path):
        sessions_file = tmp_path / "sessions.jsonl"

        # Monkey-patch SESSIONS_FILE temporarily
        import xpert.cookies as c
        old = c.SESSIONS_FILE
        c.SESSIONS_FILE = sessions_file

        try:
            save_cookies("abc123" * 8, "def456" * 8)
            data = load_cookies()
            assert data["auth_token"] == "abc123" * 8
            assert data["ct0"] == "def456" * 8
        finally:
            c.SESSIONS_FILE = old

    def test_load_nonexistent(self, tmp_path):
        import xpert.cookies as c
        old = c.SESSIONS_FILE
        c.SESSIONS_FILE = tmp_path / "nonexistent.jsonl"
        try:
            assert load_cookies() == {}
        finally:
            c.SESSIONS_FILE = old

    def test_has_cookies(self, tmp_path):
        import xpert.cookies as c
        old = c.SESSIONS_FILE
        c.SESSIONS_FILE = tmp_path / "sessions.jsonl"
        try:
            assert has_cookies() is False
            save_cookies("a" * 40, "b" * 40)
            assert has_cookies() is True
        finally:
            c.SESSIONS_FILE = old

    def test_clear_cookies(self, tmp_path):
        import xpert.cookies as c
        old = c.SESSIONS_FILE
        c.SESSIONS_FILE = tmp_path / "sessions.jsonl"
        try:
            save_cookies("a" * 40, "b" * 40)
            assert has_cookies() is True
            clear_cookies()
            assert has_cookies() is False
        finally:
            c.SESSIONS_FILE = old

    def test_save_invalid_raises(self, tmp_path):
        import xpert.cookies as c
        old = c.SESSIONS_FILE
        c.SESSIONS_FILE = tmp_path / "sessions.jsonl"
        try:
            with pytest.raises(CookieError):
                save_cookies("short", "ct0value12345678901234567890")
        finally:
            c.SESSIONS_FILE = old


# =============================================================================
# Test: Cookie Module (from test_comprehensive.py)
# =============================================================================

class TestCookieModule:
    """Tests for xpert.cookies module."""

    def test_validate_cookies_valid(self):
        """Valid hex cookies should pass validation."""
        valid, msg = validate_cookies(
            "a" * 40,  # 40 hex chars
            "b" * 40,
        )
        assert valid is True
        assert "valid" in msg.lower()

    def test_validate_cookies_token_too_short(self):
        """Token less than 20 chars should fail."""
        valid, msg = validate_cookies("abc", "b" * 40)
        assert valid is False
        assert "short" in msg.lower() or "invalid" in msg.lower()

    def test_validate_cookies_ct0_too_short(self):
        """ct0 less than 20 chars should fail."""
        valid, msg = validate_cookies("a" * 40, "abc")
        assert valid is False

    def test_validate_cookies_non_hex(self):
        """Non-hex characters should fail validation."""
        valid, msg = validate_cookies(
            "g" + "a" * 39,  # 'g' is not hex
            "b" * 40,
        )
        assert valid is False
        assert "invalid" in msg.lower() or "hex" in msg.lower()

    def test_save_and_load_cookies(self, tmp_path):
        """Saved cookies should be loadable."""
        import xpert.cookies as c
        old_file = c.SESSIONS_FILE
        c.SESSIONS_FILE = tmp_path / "sessions.jsonl"

        try:
            token = "a" * 40
            ct0 = "b" * 40
            save_cookies(token, ct0, username="testuser")

            loaded = load_cookies()
            assert loaded["auth_token"] == token
            assert loaded["ct0"] == ct0
            assert loaded["username"] == "testuser"
        finally:
            c.SESSIONS_FILE = old_file
            if tmp_path.exists():
                clear_cookies()

    def test_load_nonexistent_returns_empty_dict(self, tmp_path):
        """Loading from non-existent file should return empty dict."""
        import xpert.cookies as c
        old_file = c.SESSIONS_FILE
        c.SESSIONS_FILE = tmp_path / "nonexistent.jsonl"

        try:
            result = load_cookies()
            assert result == {}
        finally:
            c.SESSIONS_FILE = old_file

    def test_has_cookies_false_when_empty(self, tmp_path):
        """has_cookies should return False when no cookies saved."""
        import xpert.cookies as c
        old_file = c.SESSIONS_FILE
        c.SESSIONS_FILE = tmp_path / "empty.jsonl"

        try:
            clear_cookies()
            assert has_cookies() is False
        finally:
            c.SESSIONS_FILE = old_file

    def test_has_cookies_true_when_saved(self, tmp_path):
        """has_cookies should return True when cookies are saved."""
        import xpert.cookies as c
        old_file = c.SESSIONS_FILE
        c.SESSIONS_FILE = tmp_path / "has_cookies.jsonl"

        try:
            save_cookies("a" * 40, "b" * 40)
            assert has_cookies() is True
        finally:
            c.SESSIONS_FILE = old_file
            clear_cookies()

    def test_clear_cookies(self, tmp_path):
        """clear_cookies should remove the sessions file."""
        import xpert.cookies as c
        old_file = c.SESSIONS_FILE
        c.SESSIONS_FILE = tmp_path / "to_clear.jsonl"

        try:
            save_cookies("a" * 40, "b" * 40)
            assert has_cookies() is True
            clear_cookies()
            assert has_cookies() is False
        finally:
            c.SESSIONS_FILE = old_file

    def test_save_invalid_token_raises(self, tmp_path):
        """Saving invalid token should raise CookieError."""
        import xpert.cookies as c
        old_file = c.SESSIONS_FILE
        c.SESSIONS_FILE = tmp_path / "invalid.jsonl"

        try:
            with pytest.raises(CookieError):
                save_cookies("short", "b" * 40)
        finally:
            c.SESSIONS_FILE = old_file

    def test_save_invalid_ct0_raises(self, tmp_path):
        """Saving invalid ct0 should raise CookieError."""
        import xpert.cookies as c
        old_file = c.SESSIONS_FILE
        c.SESSIONS_FILE = tmp_path / "invalid_ct0.jsonl"

        try:
            with pytest.raises(CookieError):
                save_cookies("a" * 40, "short")
        finally:
            c.SESSIONS_FILE = old_file

    def test_get_cookies_status_configured(self, tmp_path):
        """get_cookies_status should return correct status when configured."""
        import xpert.cookies as c
        old_file = c.SESSIONS_FILE
        test_file = tmp_path / "status.jsonl"
        c.SESSIONS_FILE = test_file

        try:
            token = "a" * 40
            ct0 = "b" * 40
            save_cookies(token, ct0, username="testuser")

            # Now read back using the same path
            status = get_cookies_status()
            assert status["configured"] is True
            assert status["token_prefix"] == token[:8]
            assert status["ct0_prefix"] == ct0[:8]
            assert "sessions_file" in status
        finally:
            c.SESSIONS_FILE = old_file
            if test_file.exists():
                test_file.unlink()

    def test_get_cookies_status_not_configured(self, tmp_path):
        """get_cookies_status should return correct status when not configured."""
        import xpert.cookies as c
        old_file = c.SESSIONS_FILE
        c.SESSIONS_FILE = tmp_path / "no_status.jsonl"

        try:
            clear_cookies()
            status = get_cookies_status()
            assert status["configured"] is False
            assert status["token_prefix"] == ""
            assert status["ct0_prefix"] == ""
        finally:
            c.SESSIONS_FILE = old_file
