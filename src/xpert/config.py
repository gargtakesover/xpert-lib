"""Configuration for xpert."""

import os
from pathlib import Path

# Config directory
CONFIG_DIR = Path(os.path.expanduser("~/.xpert"))
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# Cookie file
COOKIE_FILE = CONFIG_DIR / "cookies.json"

# Log file
LOG_FILE = CONFIG_DIR / "xpert.log"

# Nitter instances (self-hosted + public fallback)
NITTER_INSTANCES = [
    "http://localhost:8080",
    "http://localhost:8081",
]

# User agent
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# Rate limiting
MAX_CONCURRENT_REQUESTS = 5
REQUEST_TIMEOUT = 20.0

# Cache settings
CACHE_TTL_DEFAULT = 300
CACHE_TTL_SEARCH = 120
CACHE_TTL_PROFILE = 600

# SSRF protection
SSRF_ALLOWED_HOSTS = {"x.com", "twitter.com", "nitter.net", "nitter.privacydev.net", "nitter.poast.org"}

# Cache bounds
MAX_CACHE_ENTRIES = 10000
MAX_CACHE_MEMORY_MB = 512
