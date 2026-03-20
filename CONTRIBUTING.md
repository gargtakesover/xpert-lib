# Contributing to Xpert

## Bug Reports

1. Check if Nitter is running: `xpert status`
2. Check existing issues on GitHub
3. Run with `--verbose` flag and include output

## Pull Requests

1. Fork and create a branch from `main`
2. Run tests: `python -m pytest tests/ -v`
3. Ensure mypy passes: `mypy src/`
4. Update tests for any new behavior
5. Update docs if needed

## Coding Standards

- Type hints required on all functions
- docstrings using Google style
- 100 character line limit
- Tests must have descriptive names
