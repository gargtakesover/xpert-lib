"""Configuration for xpert."""

import os
from pathlib import Path

# Package directory (engine/ is bundled alongside src/)
PACKAGE_DIR = Path(__file__).resolve().parent.parent

# Config directory (~/.xpert for miscellaneous settings)
CONFIG_DIR = Path(os.path.expanduser("~/.xpert"))
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# Engine directory (bundled Nitter Docker setup)
# Use ~/.xpert/engine for installed packages (user-writable, Docker-accessible)
# Fall back to bundled engine/ for development
if (PACKAGE_DIR / "engine").exists():
    # Development: use bundled engine/ next to source
    ENGINE_DIR = PACKAGE_DIR / "engine"
else:
    # Installed via pip: use user-writable directory Docker can access
    ENGINE_DIR = CONFIG_DIR / "engine"

# Nitter sessions file (Twitter auth tokens for Nitter)
# Stored in CONFIG_DIR (~/.xpert) for user privacy and security
SESSIONS_FILE = CONFIG_DIR / "sessions.jsonl"

# Nitter config file
NITTER_CONF = ENGINE_DIR / "nitter.conf"

# Log file
LOG_FILE = CONFIG_DIR / "xpert.log"

# Nitter instances
NITTER_INSTANCES = [
    "http://localhost:8080",
    "http://localhost:8081",
]

# User agent
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# Rate limiting
MAX_CONCURRENT_REQUESTS = 5
REQUEST_TIMEOUT = 20.0

# Default tweet limit
DEFAULT_LIMIT = 10

# Search bounds
MAX_QUERY_LENGTH = 500

# Cache settings
CACHE_TTL_DEFAULT = 300
CACHE_TTL_SEARCH = 120
CACHE_TTL_PROFILE = 600

# SSRF protection
SSRF_ALLOWED_HOSTS = {"x.com", "twitter.com", "nitter.net", "nitter.privacydev.net", "nitter.poast.org"}

# Cache bounds
MAX_CACHE_ENTRIES = 10000
MAX_CACHE_MEMORY_MB = 512
