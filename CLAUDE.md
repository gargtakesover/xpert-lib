# Xpert — CLAUDE.md

## Project Overview

Xpert is a Twitter/X data access library that scrapes Nitter instances instead of using the expensive Twitter API. It provides user profiles, timelines, search, and thread unrolling.

**Key URLs**:
- Nitter instance: http://localhost:8080
- SaaS API: http://localhost:8001

**Architecture**:
- `src/xpert/scraper.py` — Core scraping via Nitter
- `src/xpert/cookies.py` — Twitter cookie auth
- `src/xpert/circuit_breaker.py` — Failure handling
- `src/xpert/exporters.py` — CSV/JSON/Excel/Markdown export
- `src/xpert/config.py` — Configuration
- `src/xpert_cli/cli.py` — CLI interface

## Commands

```bash
# Run tests
python -m pytest tests/ -v --tb=short -m "not integration"

# Run with live Nitter tests
RUN_LIVE_TESTS=1 python -m pytest tests/ -v --tb=short

# Install
pip install -e .

# CLI
xpert user <username>
xpert timeline <username> --limit 20
xpert search <query>
xpert tweet <url>
xpert thread <url>
xpert status
xpert configure
```

## Key Conventions

1. **Never import httpx directly in scraper** — use `_build_client()` which adds auth cookies
2. **Always call `_raise_nitter_unreachable()`** before any network call
3. **Circuit breaker is global** — `nitter_circuit` in circuit_breaker.py
4. **Rate limit** — 10/min on free tier (configurable via cookies)
5. **All parse functions are pure** — return dicts, conversion to dataclasses is separate

## Testing Strategy

- Unit tests: `tests/test_*.py` (mocked)
- Integration tests: `tests/test_integration.py` (live Nitter, skip unless RUN_LIVE_TESTS=1)
- All new features need a test

## Common Issues

- **"Nitter is not reachable"** — Start Nitter: `cd ~/takeover/nitter && docker compose up -d`
- **Rate limited** — Configure cookies: `xpert configure`
- **Circuit breaker open** — Wait 30s or `docker restart nitter-private`

## Git Workflow

1. Branch: `git checkout -b feature/my-feature`
2. Commit: `git add -A && git commit -m "feat: add my feature"`
3. Push: `git push origin feature/my-feature`
4. PR: `gh pr create`

## Release Process

1. Update version in `pyproject.toml`
2. Create tag: `git tag v1.x.x && git push --tags`
3. GitHub Actions publishes to PyPI automatically
