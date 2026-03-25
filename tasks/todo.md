# Xpert Scraper Test Plan

- [x] Install project dependencies (`pip install -e ".[dev]"`)
- [x] Start Nitter instance for testing (`cd ~/takeover/nitter && docker compose up -d` or verify if it's running)
- [x] Run all automated unit tests (`python -m pytest tests/ -v --tb=short -m "not integration"`)
- [/] Run live integration tests (`RUN_LIVE_TESTS=1 python -m pytest tests/ -v --tb=short`)
- [x] Verify `xpert status` command
- [/] Verify CLI `xpert user` command
- [/] Verify CLI `xpert search` command
- [/] Verify Output formats (JSON, CSV, Excel, Markdown)
- [/] Review any failed tests and resolve them
- [ ] Document final test results in `.test/` folder
