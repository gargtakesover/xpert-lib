# Xpert

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

**Access X (Twitter) data from the command line. No API key needed.**

`xpert` is a free, open-source CLI tool and Python library that scrapes X.com through a self-hosted proxy called [Nitter](https://github.com/zedeus/nitter). It lets you fetch user profiles, timelines, search results, individual tweets, and full threads — entirely without paying for Twitter's expensive official API.

---

## What is this?

Imagine you want to read someone's tweets, search for a hashtag, or save a thread for offline reading. The official way to do this is via Twitter's API, which is highly restrictive and costs hundreds of dollars per month.

**xpert** is a free alternative. It uses a bundled, lightweight open-source tool called **Nitter** — an alternative front-end for X.com. `xpert` spins up Nitter locally using Docker and communicates with it to fetch public data from X.com using your own authenticated session tokens.

The data you get is the exact same public data you could see on X.com in your browser, but structured and easily exportable to JSON, CSV, Excel, or Markdown.

---

## Quick Start

If you already have **Python 3.9+** and **Docker** installed, you can get started in seconds:

```bash
# 1. Install xpert
pip install xpert

# 2. Add your Twitter session tokens (one-time setup)
xpert configure

# 3. Start the bundled Nitter engine (one-time setup)
xpert install

# 4. Try your first search!
xpert search "hello world" --limit 5
```

---

## Prerequisites

Before installing `xpert`, ensure you have the following system requirements:

1. **Python 3.9 or newer**: Verify your version using `python3 --version`.
2. **Docker**: `xpert` uses Docker to automatically run the Nitter backend.
   - Verify installation: `docker --version`
   - **Note:** Ensure your Docker daemon is running (e.g., Docker Desktop is open on macOS/Windows) before proceeding.

---

## Installation Guide

### Recommended Install (with bundled Engine)

Install the package and automatically set up the local Nitter Docker containers.

```bash
pip install xpert
xpert install
```

The `xpert install` command will:
- Copy the bundled Nitter engine to `~/.xpert/engine/`
- Generate a secure, random configuration key
- Start the Nitter and Redis Docker containers in the background

If you ever need to restart the engine, simply run `xpert install` again, or manually via:
`cd ~/.xpert/engine && docker compose restart`

### Library-Only Install (No Docker)

If you already host your own Nitter instance elsewhere (e.g., on a remote server), you can install `xpert` just to use the CLI and Python library:

```bash
pip install xpert
```
*(You will need to manually update `src/xpert/config.py` to point to your external instance URLs).*

---

## Authentication: Getting Your Tokens

To access non-public (logged-in-only) data, `xpert` needs your Twitter session tokens. **Your tokens never leave your local machine.**

1. Open your browser, go to [x.com](https://x.com), and log in.
2. Open **Developer Tools** (F12 or Cmd+Option+I).
3. Navigate to the **Application** (or Storage) tab.
4. Under "Cookies", select `https://x.com`.
5. Find and copy the values for these two cookies:
   - `auth_token`
   - `ct0`
6. Run the configuration wizard in your terminal:
   ```bash
   xpert configure
   ```
   Paste the tokens when prompted.
7. Verify your setup:
   ```bash
   xpert status
   ```

---

## CLI Usage & Commands

`xpert` provides several commands to scrape different types of data. You can always use the `--help` flag for detailed options on any command.

### Fetching Users
Fetch a user profile and their recent tweets.
```bash
xpert user elonmusk --limit 20
```

### Fetching Timelines
Fetch only the recent tweets from a user (no profile bio data).
```bash
xpert timeline elonmusk --format excel --output timeline.xlsx
```

### Advanced Searching
Search for tweets matching a query using powerful filters.
```bash
xpert search "python programming" --limit 50
xpert search "AI" --min-faves 100 --since 2025-01-01
xpert search "open source" --verified-only --format csv --output results.csv
xpert search "rustlang" --near "San Francisco,US" --time-within 7d
```
*Supported Filters:* `--min-faves`, `--min-retweets`, `--min-replies`, `--since`, `--until`, `--near`, `--verified-only`, `--has-engagement`, `--time-within`, `--filters (media,images,videos,links)`, `--excludes`, `--query-type (live,top,latest)`.

### Extracting Single Tweets
Scrape a single tweet by its URL.
```bash
xpert tweet https://x.com/user/status/1234567890 --format json
```

### Unrolling Threads
Expand a full thread starting from any tweet.
```bash
xpert thread https://x.com/user/status/1234567890 --format markdown --output thread.md
```

### Searching Users
Search for user accounts matching a name or keyword.
```bash
xpert search-users "python developer" --limit 10
```

---

## Output Formats

`xpert` supports exporting your data into four distinct formats using the `--format` (`-f`) flag:

- **`json` (Default)**: Raw, structured data. Best for developers, programmatic processing, and data pipelines.
- **`csv`**: Comma-separated values. Best for quick spreadsheet analysis or importing into databases.
- **`excel`**: Formatted `.xlsx` file with frozen headers and auto-filters. Best for polished reports and sharing with non-technical peers.
- **`markdown`**: A clean text table. Best for saving threads, note-taking, or pasting into documentation.

---

## Troubleshooting

- **"Connection refused"**: The local Nitter Docker container isn't running. Run `xpert install` or `xpert status` to diagnose.
- **"403 Forbidden" / Authentication Error**: Your tokens (`auth_token`, `ct0`) are expired or missing. Run `xpert configure` to update them.
- **"Rate limited"**: X.com is temporarily blocking requests due to high volume. Wait a few minutes before trying again, and lower your `--limit`.
- **Docker Mount Errors**: On certain Linux systems (e.g., sandboxes), Docker's default `overlayfs` driver may fail. You may need to configure Docker to use the `vfs` storage driver.

Always run `xpert status` first when encountering issues to get a diagnostic health check of the system.

---

## Contributing

Xpert is open source, and contributions are heavily encouraged!

1. Fork and clone the repository.
2. Install development dependencies: `pip install -e ".[dev]"`
3. Create a feature branch: `git checkout -b feature/my-feature`
4. Run tests: `pytest`
5. Ensure code formatting: `black src/` & `mypy src/`
6. Submit a Pull Request!

## License

This project is licensed under the MIT License - see the LICENSE file for details.
