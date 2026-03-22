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
