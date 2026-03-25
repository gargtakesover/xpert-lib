import pytest
import json
from xpert.cookies import save_cookies, load_cookies, clear_cookies, get_cookies_status, get_all_accounts

def test_multiple_accounts(tmp_path, monkeypatch):
    """Test saving and loading multiple accounts in sessions.jsonl."""
    sessions_file = tmp_path / "sessions.jsonl"
    monkeypatch.setattr("xpert.cookies.SESSIONS_FILE", sessions_file)

    # Initial state
    clear_cookies()
    assert get_cookies_status()["configured"] == False

    # Hex tokens >= 20 chars
    tok1 = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
    ct1 = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
    tok2 = "99999999999999999999999999999999"
    ct2 = "99999999999999999999999999999999"

    # Save first account
    save_cookies(token=tok1, ct0=ct1, username="user1", account_id="111")

    # Save second account
    save_cookies(token=tok2, ct0=ct2, username="user2", account_id="222")

    # Check all accounts
    accounts = get_all_accounts()
    assert len(accounts) == 2
    assert accounts[0]["username"] == "user1"
    assert accounts[1]["username"] == "user2"

    # Check loading a specific account
    acc1 = load_cookies(account_id="111")
    assert acc1["auth_token"] == tok1

    acc2 = load_cookies(account_id="222")
    assert acc2["auth_token"] == tok2

    # Status check with multiple accounts
    status = get_cookies_status()
    assert status["configured"] == True
    assert status["token_prefix"] == tok1[:8]

def test_load_cookies_invalid_file(tmp_path, monkeypatch):
    """Test loading cookies from a corrupted file."""
    sessions_file = tmp_path / "sessions.jsonl"
    monkeypatch.setattr("xpert.cookies.SESSIONS_FILE", sessions_file)

    sessions_file.write_text("invalid json\n")

    # Should skip invalid lines and return empty
    assert load_cookies() == {}
