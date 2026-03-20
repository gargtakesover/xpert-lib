"""Cookie management for xpert authenticated requests."""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from xpert.config import COOKIE_FILE


class CookieError(Exception):
    """Cookie validation or file error."""
    pass


def _ensure_cookie_dir():
    """Ensure cookie directory exists."""
    COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)


def save_cookies(token: str, ct0: str) -> None:
    """Save cookies to ~/.xpert/cookies.json."""
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

    _ensure_cookie_dir()
    data = {"auth_token": token, "ct0": ct0}
    with open(COOKIE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_cookies() -> dict:
    """Load cookies from ~/.xpert/cookies.json. Returns {} if not found."""
    if not COOKIE_FILE.exists():
        return {}
    try:
        with open(COOKIE_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def clear_cookies() -> None:
    """Remove stored cookies."""
    if COOKIE_FILE.exists():
        COOKIE_FILE.unlink()


def has_cookies() -> bool:
    """Check if cookies are configured."""
    cookies = load_cookies()
    return bool(cookies.get("auth_token") and cookies.get("ct0"))


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
    """Return status dict for cookie configuration."""
    cookies = load_cookies()
    configured = has_cookies()
    token = cookies.get("auth_token", "")
    ct0 = cookies.get("ct0", "")

    return {
        "configured": configured,
        "token_prefix": token[:8] if token else "",
        "ct0_prefix": ct0[:8] if ct0 else "",
        "auth_token": token,
        "ct0": ct0,
    }
