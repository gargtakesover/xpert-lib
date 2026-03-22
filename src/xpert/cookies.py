"""Cookie/session management for xpert - Nitter sessions.jsonl format.

Supports multiple Twitter accounts via JSONL format (one account per line).
Nitter reads all lines and uses the session matching the Twitter account.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional, List

from xpert.config import SESSIONS_FILE

logger = logging.getLogger(__name__)


class CookieError(Exception):
    """Cookie validation or file error."""
    pass


def _ensure_sessions_dir():
    """Ensure engine directory exists."""
    SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)


def _parse_sessions_file() -> List[dict]:
    """Parse sessions.jsonl, skipping malformed lines.

    Returns a list of valid session dicts. Malformed lines are logged and skipped.
    """
    if not SESSIONS_FILE.exists():
        return []
    sessions = []
    try:
        with open(SESSIONS_FILE) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    session = json.loads(line)
                    # Validate required fields
                    if session.get("auth_token") and session.get("ct0"):
                        sessions.append(session)
                    else:
                        logger.warning(
                            "sessions.jsonl:%d: skipping entry missing auth_token or ct0", line_num
                        )
                except json.JSONDecodeError as e:
                    logger.warning(
                        "sessions.jsonl:%d: skipping malformed JSON line: %s", line_num, e
                    )
    except IOError as e:
        logger.error("Failed to read sessions.jsonl: %s", e)
    return sessions


def save_cookies(token: str, ct0: str, username: str = "", account_id: str = "") -> None:
    """Save Twitter session tokens to sessions.jsonl (Nitter format).

    Appends a new session entry. Nitter supports multiple accounts via multiple JSONL lines.

    Args:
        token: Twitter auth_token cookie
        ct0: Twitter ct0 cookie
        username: Twitter username (for reference)
        account_id: Unique account identifier (for multi-account management)
    """
    token = token.strip()
    ct0 = ct0.strip()

    if not token or len(token) < 20:
        raise CookieError("auth_token appears invalid (too short)")
    if not ct0 or len(ct0) < 20:
        raise CookieError("ct0 appears invalid (too short)")

    if not re.match(r'^[a-f0-9]+$', token, re.IGNORECASE):
        raise CookieError("auth_token must be a hex string")
    if not re.match(r'^[a-f0-9]+$', ct0, re.IGNORECASE):
        raise CookieError("ct0 must be a hex string")

    _ensure_sessions_dir()

    # Nitter's sessions.jsonl format: one JSON object per line
    session_entry = {
        "auth_token": token,
        "ct0": ct0,
        "username": username,
        "id": account_id or username,
    }

    # Append to existing sessions (supports multi-account)
    with open(SESSIONS_FILE, "a") as f:
        f.write(json.dumps(session_entry) + "\n")

    # Restrict permissions: owner read/write only (0600)
    os.chmod(SESSIONS_FILE, 0o600)


def load_cookies(account_id: str = None) -> dict:
    """Load cookies from sessions.jsonl.

    Args:
        account_id: If provided, load the session matching this account ID.
                    If None, returns the first valid session.

    Returns:
        Session dict with auth_token and ct0, or {} if none found.
    """
    sessions = _parse_sessions_file()
    if not sessions:
        return {}
    if account_id:
        for session in sessions:
            if session.get("id") == account_id or session.get("username") == account_id:
                return session
        return {}
    return sessions[0]


def get_all_accounts() -> List[dict]:
    """Return all configured accounts from sessions.jsonl.

    Returns list of dicts with 'username', 'id', and token prefixes (never full tokens).
    """
    sessions = _parse_sessions_file()
    accounts = []
    for session in sessions:
        accounts.append({
            "username": session.get("username", ""),
            "id": session.get("id", ""),
            "token_prefix": session.get("auth_token", "")[:8],
            "ct0_prefix": session.get("ct0", "")[:8],
        })
    return accounts


def clear_cookies(account_id: str = None) -> None:
    """Remove stored sessions.

    Args:
        account_id: If provided, remove only that account's session.
                    If None, removes all sessions.
    """
    if not SESSIONS_FILE.exists():
        return
    if account_id is None:
        SESSIONS_FILE.unlink()
        return
    # Filter out the matching account
    sessions = _parse_sessions_file()
    sessions = [s for s in sessions if s.get("id") != account_id and s.get("username") != account_id]
    with open(SESSIONS_FILE, "w") as f:
        for session in sessions:
            f.write(json.dumps(session) + "\n")


def has_cookies() -> bool:
    """Check if at least one session is configured."""
    return bool(_parse_sessions_file())


def validate_cookies(token: str, ct0: str) -> tuple[bool, str]:
    """
    Validate cookie format without making a request.

    Returns (is_valid, message).
    """
    if not token or len(token) < 20:
        return False, "auth_token too short or missing"
    if not ct0 or len(ct0) < 20:
        return False, "ct0 too short or missing"
    if not re.match(r'^[a-f0-9]{20,}$', token, re.IGNORECASE):
        return False, "auth_token format invalid (must be hex, 20+ chars)"
    if not re.match(r'^[a-f0-9]{20,}$', ct0, re.IGNORECASE):
        return False, "ct0 format invalid (must be hex, 20+ chars)"
    return True, "Cookies look valid"


def get_cookies_status() -> dict:
    """Return status dict for session configuration.

    Note: Never returns full tokens for security reasons.
    """
    sessions = _parse_sessions_file()
    configured = bool(sessions)
    token = sessions[0].get("auth_token", "") if sessions else ""
    ct0 = sessions[0].get("ct0", "") if sessions else ""
    accounts = get_all_accounts()

    return {
        "configured": configured,
        "token_prefix": token[:8] if token else "",
        "ct0_prefix": ct0[:8] if ct0 else "",
        "sessions_file": str(SESSIONS_FILE),
        "account_count": len(sessions),
        "accounts": accounts,
    }
