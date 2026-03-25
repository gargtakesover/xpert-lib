# Development Guide

## Prerequisites

- Python 3.9+
- Nitter running at localhost:8080
- (Optional) Twitter cookies for higher rate limits

## Quick Start

```bash
# Clone and install
cd ~/takeover/xpert
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Start Nitter
cd ~/takeover/nitter && docker compose up -d

# Try it
xpert user elonmusk
```

## Project Structure

```
src/xpert/
├── __init__.py       # Public API exports
├── __main__.py      # python -m xpert entry
├── config.py        # Constants and config
├── cookies.py       # Cookie management
├── circuit_breaker.py # Failure handling
├── scraper.py       # Main scraping logic
└── exporters.py     # Output format handlers

src/xpert_cli/
└── cli.py           # Click-based CLI

tests/
├── conftest.py      # Fixtures
├── test_scraper.py  # Parser unit tests
├── test_cookies.py  # Cookie tests
├── test_exporters.py # Export tests
├── test_cli.py      # CLI tests
├── test_integration.py # Live API tests
└── test_circuit_breaker.py
```

## Adding a New Scraper Method

1. Add to `scraper.py`: `def my_method(...)`
2. Export from `src/xpert/__init__.py`
3. Add CLI command in `cli.py` (if needed)
4. Add unit test in `test_scraper.py`
5. Add integration test in `test_integration.py`

## Code Style

- Black formatter (line length 100)
- mypy type checking
- docstrings on all public functions
- Dataclasses for all response types
