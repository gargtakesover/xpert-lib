import pytest
from pathlib import Path
from click.testing import CliRunner
from xpert_cli.cli import main
import os
from unittest.mock import patch, MagicMock

def test_install_generates_hmac_key_when_empty(tmp_path, monkeypatch):
    # Setup mock engine directory
    engine_dir = tmp_path / "engine"
    engine_dir.mkdir()
    nitter_conf = engine_dir / "nitter.conf"
    nitter_conf.write_text('[Config]\nhmacKey = ""\n')

    # Mock necessary components to avoid actual docker calls and other side effects
    monkeypatch.setattr("xpert_cli.cli.ENGINE_DIR", engine_dir)
    monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)
    monkeypatch.setattr("xpert_cli.cli.PACKAGE_DIR", tmp_path / "package")
    (tmp_path / "package").mkdir()
    monkeypatch.setattr("xpert_cli.cli.SESSIONS_FILE", tmp_path / "sessions.jsonl")
    monkeypatch.setattr("xpert_cli.cli.check_nitter_health", lambda u: (True, "OK"))
    monkeypatch.setattr("xpert_cli.cli.NITTER_INSTANCES", ["http://localhost:8080"], raising=False)
    monkeypatch.setattr("xpert_cli.cli.cookies_module", MagicMock())

    # Mock subprocess.run to avoid Docker calls
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Docker version 20.10.7", stderr="")

        runner = CliRunner()
        result = runner.invoke(main, ["install"])

        assert result.exit_code == 0
        assert "Generated secure HMAC key." in result.output

        # Verify nitter.conf was updated
        updated_conf = nitter_conf.read_text()
        assert 'hmacKey = ""' not in updated_conf
        assert 'hmacKey = "' in updated_conf
        # It should be a 64-character hex string (32 bytes)
        import re
        match = re.search(r'hmacKey = "([a-f0-9]{64})"', updated_conf)
        assert match is not None

def test_install_generates_hmac_key_when_placeholder(tmp_path, monkeypatch):
    # Setup mock engine directory
    engine_dir = tmp_path / "engine"
    engine_dir.mkdir()
    nitter_conf = engine_dir / "nitter.conf"
    nitter_conf.write_text('[Config]\nhmacKey = "xpert-secret-key-change-in-production"\n')

    # Mock necessary components
    monkeypatch.setattr("xpert_cli.cli.ENGINE_DIR", engine_dir)
    monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)
    monkeypatch.setattr("xpert_cli.cli.PACKAGE_DIR", tmp_path / "package")
    (tmp_path / "package").mkdir()
    monkeypatch.setattr("xpert_cli.cli.SESSIONS_FILE", tmp_path / "sessions.jsonl")
    monkeypatch.setattr("xpert_cli.cli.check_nitter_health", lambda u: (True, "OK"))
    monkeypatch.setattr("xpert_cli.cli.NITTER_INSTANCES", ["http://localhost:8080"], raising=False)
    monkeypatch.setattr("xpert_cli.cli.cookies_module", MagicMock())

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Docker version 20.10.7", stderr="")

        runner = CliRunner()
        result = runner.invoke(main, ["install"])

        assert result.exit_code == 0
        assert "Generated secure HMAC key." in result.output

        # Verify nitter.conf was updated
        updated_conf = nitter_conf.read_text()
        assert "xpert-secret-key-change-in-production" not in updated_conf
        import re
        match = re.search(r'hmacKey = "([a-f0-9]{64})"', updated_conf)
        assert match is not None
