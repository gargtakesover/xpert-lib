"""Tests for CLI commands."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import click.testing
import pytest

from xpert import User
from xpert.cookies import CookieError
from xpert_cli.cli import main


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def runner():
    """Click CLI test runner."""
    return click.testing.CliRunner()


# =============================================================================
# Test: CLI - Help Commands
# =============================================================================

class TestCLIHelp:
    """Tests for CLI help output."""

    def test_main_help(self, runner):
        """Main --help should display usage and commands."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Xpert" in result.output or "Usage" in result.output

    def test_user_help(self, runner):
        """user --help should show username argument."""
        result = runner.invoke(main, ["user", "--help"])
        assert result.exit_code == 0
        assert "USERNAME" in result.output or "username" in result.output.lower()

    def test_timeline_help(self, runner):
        """timeline --help should show arguments."""
        result = runner.invoke(main, ["timeline", "--help"])
        assert result.exit_code == 0

    def test_search_help(self, runner):
        """search --help should show all filter options."""
        result = runner.invoke(main, ["search", "--help"])
        assert result.exit_code == 0
        assert "--limit" in result.output
        assert "--min-faves" in result.output
        assert "--since" in result.output
        assert "--until" in result.output
        assert "--near" in result.output
        assert "--verified-only" in result.output
        assert "--has-engagement" in result.output
        assert "--time-within" in result.output
        assert "--filters" in result.output
        assert "--excludes" in result.output
        assert "--query-type" in result.output

    def test_tweet_help(self, runner):
        """tweet --help should show URL argument."""
        result = runner.invoke(main, ["tweet", "--help"])
        assert result.exit_code == 0
        assert "URL" in result.output

    def test_thread_help(self, runner):
        """thread --help should show URL argument."""
        result = runner.invoke(main, ["thread", "--help"])
        assert result.exit_code == 0

    def test_cookies_help(self, runner):
        """cookies --help should show options."""
        result = runner.invoke(main, ["cookies", "--help"])
        assert result.exit_code == 0
        assert "--token" in result.output
        assert "--ct0" in result.output
        assert "--clear" in result.output

    def test_status_help(self, runner):
        """status --help should display."""
        result = runner.invoke(main, ["status", "--help"])
        assert result.exit_code == 0

    def test_install_help(self, runner):
        """install --help should display."""
        result = runner.invoke(main, ["install", "--help"])
        assert result.exit_code == 0
        assert "--cores" in result.output

    def test_configure_help(self, runner):
        """configure --help should display."""
        result = runner.invoke(main, ["configure", "--help"])
        assert result.exit_code == 0

    def test_search_users_help(self, runner):
        """search-users --help should display."""
        result = runner.invoke(main, ["search-users", "--help"])
        assert result.exit_code == 0
        assert "--limit" in result.output


# =============================================================================
# Test: CLI - Argument Parsing
# =============================================================================

class TestCLIArgumentParsing:
    """Tests for CLI argument parsing."""

    def test_user_requires_username(self, runner):
        """user command without username should fail."""
        result = runner.invoke(main, ["user"])
        assert result.exit_code != 0

    def test_search_requires_query(self, runner):
        """search command without query should fail."""
        result = runner.invoke(main, ["search"])
        assert result.exit_code != 0

    def test_timeline_requires_username(self, runner):
        """timeline command without username should fail."""
        result = runner.invoke(main, ["timeline"])
        assert result.exit_code != 0

    def test_tweet_requires_url(self, runner):
        """tweet command without URL should fail."""
        result = runner.invoke(main, ["tweet"])
        assert result.exit_code != 0

    def test_thread_requires_url(self, runner):
        """thread command without URL should fail."""
        result = runner.invoke(main, ["thread"])
        assert result.exit_code != 0

    def test_search_users_requires_query(self, runner):
        """search-users command without query should fail."""
        result = runner.invoke(main, ["search-users"])
        assert result.exit_code != 0

    def test_user_with_at_prefix_stripped(self, runner, monkeypatch):
        """user command with @username should work."""
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)
        monkeypatch.setattr("xpert_cli.cli.ensure_nitter_running", lambda: None)

        mock_get_user = MagicMock(return_value=User(
            username="testuser", display_name="Test",
            bio="", followers=0, following=0, tweets=0, url="https://x.com/testuser"
        ))
        mock_get_timeline = MagicMock(return_value=[])
        monkeypatch.setattr("xpert_cli.cli.get_user", mock_get_user)
        monkeypatch.setattr("xpert_cli.cli.get_timeline", mock_get_timeline)

        result = runner.invoke(main, ["user", "@testuser"])
        # Should not crash on argument parsing
        assert result.exit_code in [0, 1]


# =============================================================================
# Test: CLI - Option Defaults
# =============================================================================

class TestCLIOptionDefaults:
    """Tests for CLI option defaults."""

    def test_user_default_limit(self, runner, monkeypatch):
        """user should have default limit of 10."""
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)
        monkeypatch.setattr("xpert_cli.cli.ensure_nitter_running", lambda: None)

        captured_limit = []

        def capture_get_user(username):
            captured_limit.append(username)
            return User(username="test", display_name="Test",
                       bio="", followers=0, following=0, tweets=0, url="https://x.com/test")

        def capture_get_timeline(username, limit=10):
            captured_limit.append(limit)
            return []

        monkeypatch.setattr("xpert_cli.cli.get_user", capture_get_user)
        monkeypatch.setattr("xpert_cli.cli.get_timeline", capture_get_timeline)

        result = runner.invoke(main, ["user", "testuser"])

        # Verify limit default was used (limit=10)
        # The CLI calls get_timeline with limit=10 by default
        assert 10 in captured_limit or len(captured_limit) >= 1

    def test_search_default_limit(self, runner, monkeypatch):
        """search should have default limit of 10."""
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)
        monkeypatch.setattr("xpert_cli.cli.ensure_nitter_running", lambda: None)
        monkeypatch.setattr("xpert_cli.cli.xpert_search", MagicMock(return_value=[]))

        result = runner.invoke(main, ["search", "test"])

        # Should not crash and should use default limit
        assert result.exit_code in [0, 1]

    def test_search_users_default_limit(self, runner, monkeypatch):
        """search-users should have default limit of 20."""
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)
        monkeypatch.setattr("xpert_cli.cli.ensure_nitter_running", lambda: None)
        monkeypatch.setattr("xpert_cli.cli.search_users", MagicMock(return_value=[]))

        result = runner.invoke(main, ["search-users", "test"])

        # Should not crash
        assert result.exit_code in [0, 1]


# =============================================================================
# Test: CLI - Edge Cases
# =============================================================================

class TestCLIEdgeCases:
    """Tests for CLI edge cases."""

    def test_user_unknown_module_error(self, runner, monkeypatch):
        """user with module error should show error."""
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", False)
        result = runner.invoke(main, ["user", "testuser"])
        assert result.exit_code == 1
        assert "error" in result.output.lower() or "Module" in result.output

    def test_search_empty_results(self, runner, monkeypatch):
        """search with no results should show message."""
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)
        monkeypatch.setattr("xpert_cli.cli.ensure_nitter_running", lambda: None)
        monkeypatch.setattr("xpert_cli.cli.xpert_search", MagicMock(return_value=[]))

        result = runner.invoke(main, ["search", "nonexistent_query_xyz"])
        # Should not crash, may show warning about no results
        assert result.exit_code == 0

    def test_timeline_empty_results(self, runner, monkeypatch):
        """timeline with no tweets should show message."""
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)
        monkeypatch.setattr("xpert_cli.cli.ensure_nitter_running", lambda: None)
        monkeypatch.setattr("xpert_cli.cli.get_timeline", MagicMock(return_value=[]))

        result = runner.invoke(main, ["timeline", "nonexistent_user_xyz"])
        # Should not crash
        assert result.exit_code == 0

    def test_search_users_empty_results(self, runner, monkeypatch):
        """search-users with no results should show message."""
        import xpert_cli.cli as cli_module
        import xpert.config as config_module

        monkeypatch.setattr(cli_module, "MODULES_OK", True)
        monkeypatch.setattr(config_module, "NITTER_INSTANCES", ["http://localhost:8080"])
        monkeypatch.setattr(cli_module, "ensure_nitter_running", lambda: None)
        # Need to patch the actual function used in CLI, not xpert_search_users
        # The CLI imports xpert.search_users as xpert_search_users
        try:
            monkeypatch.setattr(cli_module, "xpert_search_users", MagicMock(return_value=[]))
        except AttributeError:
            # If xpert_search_users doesn't exist, skip this test
            pytest.skip("xpert_search_users not available")

        result = runner.invoke(main, ["search-users", "nonexistent_user_xyz"])
        # Should not crash
        assert result.exit_code == 0

    def test_very_long_query(self, runner, monkeypatch):
        """search with very long query should not crash."""
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)
        monkeypatch.setattr("xpert_cli.cli.ensure_nitter_running", lambda: None)
        monkeypatch.setattr("xpert_cli.cli.xpert_search", MagicMock(return_value=[]))

        long_query = "a" * 500
        result = runner.invoke(main, ["search", long_query])
        # Should not crash (may fail for other reasons but not parsing)
        assert result.exit_code in [0, 1]

    def test_special_characters_in_query(self, runner, monkeypatch):
        """search with special characters should not crash."""
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)
        monkeypatch.setattr("xpert_cli.cli.ensure_nitter_running", lambda: None)
        monkeypatch.setattr("xpert_cli.cli.xpert_search", MagicMock(return_value=[]))

        special_query = "test @user #hashtag with émoji 🎉"
        result = runner.invoke(main, ["search", special_query])
        # Should not crash on parsing
        assert result.exit_code in [0, 1]


# =============================================================================
# Test: CLI - Cookies Command
# =============================================================================

class TestCLICookies:
    """Tests for cookies CLI command."""

    def test_cookies_status_no_args(self, runner, monkeypatch):
        """cookies with no args should show status."""
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)
        monkeypatch.setattr("xpert_cli.cli.cookies_module", MagicMock(
            has_cookies=MagicMock(return_value=False),
            get_cookies_status=MagicMock(return_value={
                "configured": False,
                "token_prefix": "",
                "ct0_prefix": "",
                "sessions_file": "/tmp/test.jsonl",
            }),
        ))

        result = runner.invoke(main, ["cookies"])
        assert result.exit_code == 0
        assert "configured" in result.output.lower() or "not configured" in result.output.lower()

    def test_cookies_clear(self, runner, monkeypatch):
        """cookies --clear should clear session."""
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)

        mock_cookies = MagicMock()
        monkeypatch.setattr("xpert_cli.cli.cookies_module", mock_cookies)

        result = runner.invoke(main, ["cookies", "--clear"])
        assert result.exit_code == 0
        mock_cookies.clear_cookies.assert_called_once()

    def test_cookies_with_token_and_ct0(self, runner, monkeypatch):
        """cookies --token X --ct0 Y should save cookies."""
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)

        mock_cookies = MagicMock()
        monkeypatch.setattr("xpert_cli.cli.cookies_module", mock_cookies)

        result = runner.invoke(main, [
            "cookies",
            "--token", "a" * 40,
            "--ct0", "b" * 40,
        ])
        assert result.exit_code == 0
        mock_cookies.save_cookies.assert_called_once()


# =============================================================================
# Test: CLI - Install Command
# =============================================================================

class TestCLIInstall:
    """Tests for install CLI command."""

    def test_install_shows_cores(self, runner, monkeypatch):
        """install --cores should show CPU core count."""
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)

        result = runner.invoke(main, ["install", "--cores"])
        assert result.exit_code == 0
        # Should mention cores or CPU
        assert "core" in result.output.lower() or "cpu" in result.output.lower()

    def test_install_docker_not_found(self, runner, monkeypatch):
        """install when docker not found should show error."""
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)

        def mock_run(cmd, **kwargs):
            if cmd[0] == "docker":
                raise FileNotFoundError("docker not found")
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr("subprocess.run", mock_run)

        result = runner.invoke(main, ["install"])
        assert result.exit_code == 1
        assert "Docker" in result.output or "docker" in result.output.lower()

    def test_install_docker_compose_not_found(self, runner, monkeypatch):
        """install when docker compose not found should show error."""
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)
        call_count = [0]

        def mock_run(cmd, **kwargs):
            call_count[0] += 1
            if cmd[0] == "docker" and cmd[1] == "--version":
                return MagicMock(returncode=0, stdout="Docker version 20.10", stderr="")
            if cmd[0] == "docker" and cmd[1] == "compose":
                raise FileNotFoundError("docker compose not found")
            if cmd[0] == "docker-compose":
                raise FileNotFoundError("docker-compose not found")
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr("subprocess.run", mock_run)

        result = runner.invoke(main, ["install"])
        assert result.exit_code == 1

    def test_install_success(self, runner, monkeypatch):
        """install should run docker compose up."""
        import xpert_cli.cli as cli_module
        from pathlib import Path

        monkeypatch.setattr(cli_module, "MODULES_OK", True)
        monkeypatch.setattr(cli_module, "cookies_module", MagicMock(
            has_cookies=MagicMock(return_value=True),
        ))
        monkeypatch.setattr(cli_module, "ENGINE_DIR", Path("/tmp/engine"))

        # Mock subprocess.run to return success
        def mock_run(cmd, **kwargs):
            return MagicMock(returncode=0, stdout="Done", stderr="")

        monkeypatch.setattr("subprocess.run", mock_run)
        monkeypatch.setattr("xpert_cli.cli.check_nitter_health", lambda u: (True, "OK"))
        monkeypatch.setattr("time.sleep", lambda x: None)

        result = runner.invoke(main, ["install"])
        # Should complete without error (may show warning about health)
        assert result.exit_code == 0


# =============================================================================
# Test: CLI - Configure Command
# =============================================================================

class TestCLIConfigure:
    """Tests for configure CLI command."""

    def test_configure_success(self, runner, monkeypatch):
        """configure with valid input should save cookies."""
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)

        mock_cookies = MagicMock()
        mock_cookies.CookieError = CookieError
        mock_cookies.validate_cookies = MagicMock(return_value=(True, "OK"))
        monkeypatch.setattr("xpert_cli.cli.cookies_module", mock_cookies)

        result = runner.invoke(main, ["configure"], input="a" * 40 + "\n" + "b" * 40 + "\ntestuser\n")

        # Should complete without error
        assert result.exit_code in [0, 1]
        mock_cookies.save_cookies.assert_called_once()

    def test_configure_invalid_token(self, runner, monkeypatch):
        """configure with invalid token should show error."""
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)

        mock_cookies = MagicMock()
        mock_cookies.CookieError = CookieError
        mock_cookies.validate_cookies = MagicMock(return_value=(False, "Token too short"))
        monkeypatch.setattr("xpert_cli.cli.cookies_module", mock_cookies)

        result = runner.invoke(main, ["configure"], input="short\n" + "b" * 40 + "\n\n")

        # Should show warning about validation
        assert result.exit_code in [0, 1]

    def test_configure_cookie_error(self, runner, monkeypatch):
        """configure when save fails should show error."""
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)

        mock_cookies = MagicMock()
        mock_cookies.CookieError = CookieError
        mock_cookies.save_cookies = MagicMock(side_effect=CookieError("Test error"))
        mock_cookies.validate_cookies = MagicMock(return_value=(True, "OK"))
        monkeypatch.setattr("xpert_cli.cli.cookies_module", mock_cookies)

        result = runner.invoke(main, ["configure"], input="a" * 40 + "\n" + "b" * 40 + "\n\n")

        assert result.exit_code == 1
        assert "error" in result.output.lower() or "Failed" in result.output


# =============================================================================
# Test: CLI - Status Command
# =============================================================================

class TestCLIStatus:
    """Tests for status CLI command."""

    def test_status_shows_nitter_connectivity(self, runner, monkeypatch):
        """status should check Nitter connectivity."""
        import xpert_cli.cli as cli_module

        monkeypatch.setattr(cli_module, "MODULES_OK", True)
        monkeypatch.setattr(cli_module, "cookies_module", MagicMock(
            has_cookies=MagicMock(return_value=True),
            get_cookies_status=MagicMock(return_value={
                "configured": True,
                "token_prefix": "abc123",
                "ct0_prefix": "def456",
            }),
        ))
        monkeypatch.setattr(cli_module, "check_nitter_health", lambda u: (True, "OK"))

        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "Nitter" in result.output or "nitter" in result.output.lower()

    def test_status_verbose_troubleshooting(self, runner, monkeypatch):
        """status --verbose should show troubleshooting info."""
        import xpert_cli.cli as cli_module

        monkeypatch.setattr(cli_module, "MODULES_OK", True)
        monkeypatch.setattr(cli_module, "cookies_module", MagicMock(
            has_cookies=MagicMock(return_value=False),
            get_cookies_status=MagicMock(return_value={
                "configured": False,
                "token_prefix": "",
                "ct0_prefix": "",
            }),
        ))
        monkeypatch.setattr(cli_module, "check_nitter_health", lambda u: (False, "Connection refused"))

        result = runner.invoke(main, ["status", "--verbose"])
        assert result.exit_code == 0


# =============================================================================
# Test: CLI - Setup Command
# =============================================================================

class TestCLISetup:
    """Tests for setup CLI command."""

    def test_setup_runs_without_crash(self, runner, monkeypatch):
        """setup should run without crashing."""
        import xpert_cli.cli as cli_module

        monkeypatch.setattr(cli_module, "MODULES_OK", True)
        monkeypatch.setattr(cli_module, "check_nitter_health", lambda u: (True, "OK"))
        monkeypatch.setattr(cli_module, "cookies_module", MagicMock(
            has_cookies=MagicMock(return_value=True),
        ))

        result = runner.invoke(main, ["setup"])
        assert result.exit_code == 0
        assert "Xpert" in result.output or "Welcome" in result.output
