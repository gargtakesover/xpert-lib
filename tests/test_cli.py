"""Integration tests for xpert CLI."""

import pytest
import tempfile
import json
from unittest.mock import patch, MagicMock
import click.testing

from xpert_cli.cli import main


@pytest.fixture
def runner():
    return click.testing.CliRunner()


class TestHelp:
    def test_cli_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Xpert" in result.output

    def test_user_help(self, runner):
        result = runner.invoke(main, ["user", "--help"])
        assert result.exit_code == 0
        assert "USERNAME" in result.output

    def test_search_help(self, runner):
        result = runner.invoke(main, ["search", "--help"])
        assert result.exit_code == 0
        assert "QUERY" in result.output

    def test_cookies_help(self, runner):
        result = runner.invoke(main, ["cookies", "--help"])
        assert result.exit_code == 0

    def test_status_help(self, runner):
        result = runner.invoke(main, ["status", "--help"])
        assert result.exit_code == 0


class TestCookies:
    def test_cookies_status_no_cookies(self, runner, monkeypatch):
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)
        monkeypatch.setattr("xpert_cli.cli.cookies_module", None)
        result = runner.invoke(main, ["cookies"])
        # Should not crash
        assert result.exit_code in [0, 1]

    def test_configure_prompts(self, runner, monkeypatch, tmp_path):
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)

        mock_save = MagicMock()
        mock_cookie_mod = MagicMock()
        mock_cookie_mod.save_cookies = mock_save
        mock_cookie_mod.CookieError = Exception
        mock_cookie_mod.validate_cookies = lambda t, c: (True, "OK")
        monkeypatch.setattr("xpert_cli.cli.cookies_module", mock_cookie_mod)

        result = runner.invoke(main, ["configure"], input="abc123def456\nabc123def456\n")
        # Should complete without crash
        assert result.exit_code in [0, 1]


class TestUserCommand:
    def test_user_no_args(self, runner):
        result = runner.invoke(main, ["user"])
        assert result.exit_code != 0

    def test_user_unknown_module(self, runner, monkeypatch):
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", False)
        result = runner.invoke(main, ["user", "testuser"])
        assert result.exit_code == 1
        assert "Module error" in result.output


class TestSearchCommand:
    def test_search_no_args(self, runner):
        result = runner.invoke(main, ["search"])
        assert result.exit_code != 0


class TestTimelineCommand:
    def test_timeline_no_args(self, runner):
        result = runner.invoke(main, ["timeline"])
        assert result.exit_code != 0


class TestTweetCommand:
    def test_tweet_no_args(self, runner):
        result = runner.invoke(main, ["tweet"])
        assert result.exit_code != 0


class TestSetup:
    def test_setup_no_crash(self, runner, monkeypatch):
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)
        monkeypatch.setattr("xpert_cli.cli.check_nitter_health", lambda u: (True, "OK"))
        monkeypatch.setattr("xpert_cli.cli.cookies_module", MagicMock(has_cookies=lambda: True))
        result = runner.invoke(main, ["setup"])
        assert "Xpert" in result.output


class TestStatus:
    def test_status_no_crash(self, runner, monkeypatch):
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)
        monkeypatch.setattr("xpert_cli.cli.cookies_module", MagicMock(
            has_cookies=lambda: True,
            get_cookies_status=lambda: {"configured": True, "token_prefix": "abc", "ct0_prefix": "def"},
        ))
        monkeypatch.setattr("xpert_cli.cli.check_nitter_health", lambda u: (True, "OK"))
        result = runner.invoke(main, ["status"])
        assert "Xpert" in result.output
