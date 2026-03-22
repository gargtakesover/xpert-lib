# xpert

```
 ██████╗ ██████╗ ██╗██████╗ ██╗██████╗  ██████╗ ███╗   ██╗
██╔════╝ ██╔══██╗██║██╔══██╗██║██╔══██╗██╔═══██╗████╗  ██║
██║  ███╗██████╔╝██║██║  ██║██║██████╔╝██║   ██║██╔██╗ ██║
██║   ██║██╔══██╗██║██║  ██║██║██╔══██╗██║   ██║██║╚██╗██║
╚██████╔╝██║  ██║██║██████╔╝██║██║  ██║╚██████╔╝██║ ╚████║
 ╚═════╝ ╚═╝  ╚═╝╚═╝╚═════╝ ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
```

**Access X (Twitter) data from the command line. No API key needed.**

`xpert` is a free, open-source CLI tool that scrapes X.com through a self-hosted proxy called [Nitter](https://github.com/zedeus/nitter). It lets you fetch user profiles, timelines, search results, individual tweets, and full threads -- all without paying $100+/month for Twitter's official API.

---

## What is this?

Imagine you want to read someone's tweets, search for a hashtag, or save a thread for offline reading. The official way to do this is Twitter's API -- but it costs money (hundreds of dollars per month) and requires an application approval process.

**xpert** is a free alternative. Instead of going through Twitter's expensive API, it uses a lightweight open-source tool called **Nitter**, which is basically a lightweight, open-source mirror of X.com that anyone can run on their own computer. xpert talks to your local Nitter instance, which in turn fetches public data from X.com using your own logged-in session.

Think of it like this:
- **Twitter's API** = a paid toll road ($100+/month)
- **xpert + Nitter** = a free cycling path that uses your own legs (your X.com account)

The data you get is the same public data you could see on X.com yourself -- xpert just makes it easy to grab it programmatically and export it to files.

---

## Quick Start (30 seconds)

If you already have Python and Docker, run these four commands and you are off:

```bash
# 1. Install xpert
pip install -e .

# 2. Add your Twitter session tokens (one-time setup)
xpert configure

# 3. Start the bundled Nitter engine (one-time setup)
xpert install

# 4. Try your first search
xpert search "hello world" --limit 5
```

That is it. You now have tweets in your terminal. Keep reading for detailed setup steps.

---

## Prerequisites

Before you install xpert, make sure you have two things on your computer:

### Python 3.9 or newer

Python is the programming language xpert is written in. Check if you have it:

```bash
python3 --version
```

You should see something like `Python 3.11.5`. If you see an error, download Python from [python.org](https://python.org/downloads/) or via your system package manager:

```bash
# macOS
brew install python3

# Ubuntu / Debian
sudo apt install python3 python3-pip

# Fedora / RHEL / Oracle Linux
sudo dnf install python3
```

### Docker

**Docker** is a tool that lets you run small, isolated "containers" on your computer -- like a separate tiny computer inside your machine. xpert uses Docker to run Nitter (the tool that talks to X.com) automatically, so you do not have to install or configure Nitter manually.

Check if Docker is installed:

```bash
docker --version
```

If you see something like `Docker version 27.x.x`, you are good. If not, install Docker:

- **macOS / Windows**: Download [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Linux**: Follow the [official install guide](https://docs.docker.com/engine/install/)

After installing Docker, **open Docker Desktop** (or start the Docker daemon on Linux) before running `xpert install`. You should see a small whale icon in your menu bar when Docker is running.

---

## Installation Guide

Choose the method that fits your situation.

### Method A: Full Install (with bundled Nitter engine) -- Recommended

This installs xpert **and** automatically sets up the Nitter Docker containers in the background. This is the easiest path.

```bash
pip install -e .
```

The `-e` flag means "editable install" -- it installs the package but keeps the source code in place so you can edit it. For a normal install without editable mode:

```bash
pip install .
```

After installation, run:

```bash
xpert install
```

This command:
1. Copies the bundled Nitter engine to `~/.xpert/engine/`
2. Generates a random security key for Nitter
3. Starts the Nitter and Redis Docker containers
4. Waits for Nitter to come online

If you ever need to restart Nitter, just run `xpert install` again or:

```bash
cd ~/.xpert/engine && docker compose up -d
```

### Method B: Python library only (no Docker)

If you already have a Nitter instance running somewhere (e.g., at `http://localhost:8080`), you can install xpert as a Python library without the Docker engine:

```bash
pip install xpert
```

Then make sure your existing Nitter is reachable and configure your session tokens:

```bash
xpert configure
```

Set the `NITTER_INSTANCES` in `src/xpert/config.py` to point to your existing instance.

---

## How to Get Your Twitter Tokens

xpert needs your Twitter session tokens to access non-public (logged-in-only) data. Here is how to find them:

### Step 1: Open Twitter in Your Browser

Go to [twitter.com](https://twitter.com) and make sure you are logged in.

### Step 2: Open Developer Tools

Press **F12** on your keyboard (or **Cmd+Option+I** on Mac). A panel will appear at the bottom or side of your screen.

### Step 3: Go to the Application Tab

Click the **"Application"** tab (it may be labeled with a little storage cube icon). In the left sidebar under "Storage", click **"Cookies"** and then click on `https://twitter.com`.

### Step 4: Find the Tokens

Look for two entries:

| Cookie Name | What it is |
|-------------|------------|
| `auth_token` | Your main session token (long hex string) |
| `ct0` | Your CSRF token (also a long hex string) |

Click on each one, copy the **Value** field (not the Name field). These are your tokens.

### Step 5: Enter Them in xpert

```bash
xpert configure
```

Paste your `auth_token` when asked, then paste your `ct0` when asked. Optionally enter your Twitter username.

### Step 6: Verify

```bash
xpert status
```

You should see `Cookies configured` with a token prefix like `a1b2c3d4...`. This means xpert is authenticated and ready.

### How Often Do Tokens Expire?

Twitter session tokens typically last **several months**, but they can expire sooner if you log out, change your password, or Twitter detects suspicious activity. If xpert suddenly stops working and you see authentication errors, re-run `xpert configure` with fresh tokens.

---

## All CLI Commands and Options

### Global Flags

| Flag | Type | Description |
|------|------|-------------|
| `--version` | flag | Show xpert version |
| `--help` | flag | Show help for any command |

---

### `xpert install`

First-time setup. Starts the bundled Nitter engine via Docker.

```bash
xpert install
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--cores` | flag | -- | Show available CPU cores (diagnostic) |

---

### `xpert configure`

Interactive setup wizard to save Twitter session tokens to `sessions.jsonl`.

```bash
xpert configure
```

**No options.** This command asks interactive questions. See the "How to Get Your Twitter Tokens" section above for a step-by-step guide.

---

### `xpert user <username>`

Fetch a user profile and their recent tweets.

```bash
xpert user elonmusk --limit 20
xpert user @elonmusk --limit 20
xpert user elonmusk --format csv --output my_tweets.csv
```

| Option | Type | Default | Description | Example |
|--------|------|---------|-------------|---------|
| `--limit`, `-n` | integer | `10` | Number of recent tweets to fetch | `--limit 50` |
| `--format`, `-f` | choice | `json` | Output format (json/csv/excel/markdown) | `--format csv` |
| `--output`, `-o` | string | stdout | Write output to a file | `--output tweets.json` |

**Note:** Profile data can only be exported as JSON. CSV, Excel, and Markdown formats are for tweet data only.

---

### `xpert timeline <username>`

Fetch a user's timeline (their recent tweets only, no profile info).

```bash
xpert timeline elonmusk --limit 20
xpert timeline elonmusk --format excel --output timeline.xlsx
```

| Option | Type | Default | Description | Example |
|--------|------|---------|-------------|---------|
| `--limit`, `-n` | integer | `10` | Number of tweets to fetch | `--limit 100` |
| `--format`, `-f` | choice | `json` | Output format (json/csv/excel/markdown) | `--format excel` |
| `--output`, `-o` | string | stdout | Write output to a file | `--output out.csv` |

---

### `xpert search <query>`

Search for tweets matching a query. This is the most powerful command with many filter options.

```bash
xpert search "python programming" --limit 20
xpert search "AI" --min-faves 100 --since 2025-01-01
xpert search "open source" --verified-only --format csv --output results.csv
xpert search "rustlang" --near "San Francisco,US" --time-within 7d
xpert search "news" --filters media --query-type top --limit 50
```

| Option | Type | Default | Description | Example |
|--------|------|---------|-------------|---------|
| `--limit`, `-n` | integer | `10` | Number of results | `--limit 50` |
| `--min-faves` | integer | -- | Minimum likes | `--min-faves 500` |
| `--min-retweets` | integer | -- | Minimum retweets | `--min-retweets 100` |
| `--min-replies` | integer | -- | Minimum replies | `--min-replies 50` |
| `--min-engagement` | integer | -- | Min total engagement (likes+retweets+replies) | `--min-engagement 1000` |
| `--since` | string | -- | Tweets after this date (YYYY-MM-DD) | `--since 2025-06-01` |
| `--until` | string | -- | Tweets before this date (YYYY-MM-DD) | `--until 2025-06-30` |
| `--near` | string | -- | Near a city and country | `--near "Berlin,DE"` |
| `--verified-only` | flag | False | Only verified accounts | `--verified-only` |
| `--has-engagement` | flag | False | Exclude zero-engagement tweets | `--has-engagement` |
| `--time-within` | choice | -- | Relative time window | `--time-within 24h` |
| `--filters` | string | -- | Include only: media,images,videos,links | `--filters media,videos` |
| `--excludes` | string | -- | Exclude: media,videos | `--excludes videos` |
| `--query-type` | choice | `live` | Sort by: live/top/latest | `--query-type top` |
| `--format`, `-f` | choice | `json` | Output format | `--format csv` |
| `--output`, `-o` | string | stdout | Write to file | `--output results.csv` |

**Valid `--time-within` values:** `25m`, `6h`, `24h`, `7d`

**Valid `--filters` values (comma-separated):** `media`, `images`, `videos`, `links`

**Valid `--excludes` values (comma-separated):** `media`, `videos`

**Valid `--query-type` values:**
- `live` -- Most relevant tweets (default)
- `top` -- Most popular/highest engagement
- `latest` -- Most recent

---

### `xpert search-users <query>`

Search for user accounts matching a name or keyword.

```bash
xpert search-users "python developer"
xpert search-users "open source" --limit 20
```

| Option | Type | Default | Description | Example |
|--------|------|---------|-------------|---------|
| `--limit`, `-n` | integer | `10` | Number of results | `--limit 20` |
| `--format`, `-f` | choice | `json` | Output format (JSON only) | `--format json` |
| `--output`, `-o` | string | stdout | Write to file | `--output users.json` |

---

### `xpert tweet <url>`

Scrape a single tweet by its URL.

```bash
xpert tweet https://x.com/elonmusk/status/1234567890
xpert tweet https://twitter.com/elonmusk/status/1234567890 --format json
```

Accepts URLs from `x.com`, `twitter.com`, and Nitter instances.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--format`, `-f` | choice | `json` | Output format |
| `--output`, `-o` | string | stdout | Write to file |

---

### `xpert thread <url>`

Unroll (expand) a full thread starting from any tweet in the thread.

```bash
xpert thread https://x.com/elonmusk/status/1234567890
xpert thread https://x.com/elonmusk/status/1234567890 --format markdown --output thread.md
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--format`, `-f` | choice | `json` | Output format |
| `--output`, `-o` | string | stdout | Write to file |

---

### `xpert status`

Check the health of your xpert installation. Always run this first when something goes wrong.

```bash
xpert status
xpert status --verbose
```

| Option | Type | Description |
|--------|------|-------------|
| `--verbose`, `-v` | flag | Show detailed troubleshooting steps |

The output tells you:
- Whether your Twitter session tokens are configured
- Whether Nitter is reachable (and at which URLs)
- What to do next to get xpert working

---

### `xpert cookies`

Manage your Twitter session tokens.

```bash
# Show current status
xpert cookies

# Save tokens directly (non-interactive)
xpert cookies --token YOUR_AUTH_TOKEN --ct0 YOUR_CT0

# Clear saved tokens
xpert cookies --clear
```

| Option | Type | Description |
|--------|------|-------------|
| `--token` | string | `auth_token` value |
| `--ct0` | string | `ct0` value |
| `--clear` | flag | Remove saved tokens |

---

### `xpert setup`

Interactive first-time setup wizard. Run this if you are new and want guidance through the whole setup process.

```bash
xpert setup
```

Walks you through checking Python version, Nitter connectivity, and session token status, then prints a personalized next-steps checklist.

---

## The `--format` Question: Which Format Should I Use?

xpert supports four output formats. Here is when to use each:

### `json` (default)

**Best for:** Developers, scripts, data pipelines, programmatic processing.

JSON is raw structured data -- every tweet's fields (author, text, likes, retweets, date, etc.) are laid out in a machine-readable tree. This is what you would use if you are building something that consumes this data.

```bash
xpert search "rustlang" --limit 20 --format json
```

### `csv`

**Best for:** Spreadsheet analysis, Google Sheets import, basic data exploration.

CSV (Comma-Separated Values) puts each tweet on a line, with columns separated by commas. Every row has the same columns. Open it in Excel, Google Sheets, or LibreOffice Calc.

```bash
xpert timeline elonmusk --limit 50 --format csv --output tweets.csv
```

Then open `tweets.csv` in Excel and sort/filter by likes, retweets, or date.

### `excel`

**Best for:** Polished reports, formatted spreadsheets, sharing with non-technical colleagues.

Excel (.xlsx) is like CSV but with styled headers (X blue), frozen header row, and auto-filters already set up. Requires `pandas` and `openpyxl` (included by default in xpert).

```bash
xpert search "AI news" --limit 100 --format excel --output analysis.xlsx
```

### `markdown`

**Best for:** Saving threads, note-taking, pasting into documentation or a blog.

Markdown produces a clean text table of tweets. Perfect for copying into a README, a GitHub issue, or a note file. Shows truncated text (50 chars) to keep it readable.

```bash
xpert thread https://x.com/user/status/123 --format markdown --output thread.md
```

---

## How xpert Actually Works (The Short Version)

You do not need to understand this to use xpert, but it helps when things go wrong.

```
You (terminal)
│
│ xpert search "hello"
│
▼
┌──────────────────┐     Scrapes HTML      ┌───────────────┐
│  xpert Python    │ ───────────────────────▶│  Nitter       │
│  CLI + library   │◀───────────────────────│  (Docker)     │
└──────────────────┘     Returns data        │  localhost    │
│                               │            │  :8080        │
│ Converts HTML ────────────────┘            └──────┬────────┘
▼                                                 ▼
Terminal output                             ┌───────────────┐
                                             │ Twitter/X.com │
                                             │ (your account │
                                             │  via cookies) │
                                             └───────────────┘
```

**Step by step:**

1. You type `xpert search "hello"` in your terminal
2. xpert's Python code sends an HTTP request to your local Nitter server (running in Docker at `localhost:8080`)
3. Nitter uses your session tokens from `sessions.jsonl` to fetch the X.com page, the same way your browser would
4. Nitter returns the HTML page
5. xpert parses the HTML (using BeautifulSoup) into clean Python objects (Tweet, User)
6. xpert formats and displays or saves the results

**Why this matters:**

- **Nitter runs locally** -- it is not a third-party service. Your tokens never leave your machine.
- **sessions.jsonl** -- This file holds your Twitter cookies. It is chmod `0600` (readable only by you) and is stored in `~/.xpert/`, not in the project directory.
- **Circuit breaker** -- If Nitter or X.com is having issues, xpert's circuit breaker automatically stops hammering it and waits before retrying (prevents you from getting rate-limited further).
- **Multi-instance fallback** -- If one Nitter instance is down, xpert automatically tries the next one in the list (`localhost:8081`).

---

## Troubleshooting

### "Connection refused" / Nitter not reachable

**Error:** `Connection error: Connection refused`

**What happened:** xpert cannot reach the Nitter server running on your computer.

**Fix:**

```bash
# 1. Check if Docker containers are running
docker ps | grep nitter

# 2. If not, start them
cd ~/.xpert/engine && docker compose up -d

# 3. Or use xpert's install command
xpert install

# 4. Verify
xpert status
```

---

### "403 Forbidden" / Authentication error

**Error:** Nitter returns a 403 or authentication error.

**What happened:** Your Twitter session tokens are missing, expired, or invalid.

**Fix:**

```bash
# Check token status
xpert cookies

# Re-configure if needed
xpert configure
```

Your tokens may have expired. Get fresh ones from your browser (see the "How to Get Your Twitter Tokens" section).

---

### "Rate limited"

**Error:** `Rate limited: ... Please wait a moment and try again.`

**What happened:** You are making too many requests to X.com in a short time. This is not an xpert bug -- it is X.com's anti-bot protection.

**Fix:**

- Wait 30 seconds to a few minutes before retrying.
- Reduce your `--limit` values.
- Use `--time-within 7d` instead of fetching large time ranges.
- Note: xpert has a circuit breaker that will naturally slow down after consecutive failures.

---

### "Invalid date format"

**Error:** `Invalid --since date: 'june 1'. Use YYYY-MM-DD format.`

**What happened:** You passed a date in a human-readable format (`june 1`, `June 1st`, `1/6/25`) instead of the required `YYYY-MM-DD` format.

**Fix:** Use the correct format:

```bash
# Wrong
xpert search "hello" --since "June 1 2025"

# Correct
xpert search "hello" --since 2025-06-01 --until 2025-06-30
```

---

### "Query too long"

**Error:** `Query too long (537 chars). Maximum is 500.`

**What happened:** Your search query (including all the filters added automatically) exceeds 500 characters.

**Fix:**

- Shorten your query
- Reduce the number of `--filters` you are adding
- Split the search into multiple smaller queries

---

### "Path traversal blocked"

**Error:** `Error: Output path must be within current directory`

**What happened:** You tried to write to a path outside your current working directory. xpert blocks this for security.

**Fix:** Use an absolute path or a path relative to your current working directory:

```bash
# Wrong (from /home/user):
xpert search "hello" --output /etc/results.csv

# Correct
xpert search "hello" --output ./results.csv
xpert search "hello" --output /home/user/results.csv
```

---

### "Circuit breaker is open"

**Error:** `Circuit breaker is open. Too many failures. Retry in 30s.`

**What happened:** xpert tried to reach Nitter multiple times and failed repeatedly. The circuit breaker "tripped" to prevent further damage.

**Fix:**

```bash
# Wait 30 seconds, then:
xpert status

# If Nitter is still not responding:
docker restart xpert-nitter
```

---

### "Module error" / xpert not installed properly

**Error:** `Module error: No module named 'xpert'`

**What happened:** xpert is not in your Python path.

**Fix:**

```bash
# Reinstall
pip install -e /home/opc/takeover/xpert

# Or install the package
pip install /home/opc/takeover/xpert
```

---

## Where Are the Logs?

xpert currently has **no structured log file**. Error messages are printed to your terminal (stderr) but not saved to disk.

However, two files are relevant:

### `~/.xpert/sessions.jsonl`

Your Twitter session tokens. Stored in your home directory, chmod `0600` (owner-only). This is the most sensitive file xpert uses.

**Do not share this file.** It contains your Twitter session cookies which grant access to your account.

**Location:** `~/.xpert/sessions.jsonl`

```bash
# Check it exists
ls -la ~/.xpert/sessions.jsonl
```

### `~/.xpert/xpert.log`

Currently **unused** -- xpert does not write structured logs yet. This file may be created in a future version. For now, error messages go directly to your terminal.

### `~/.xpert/engine/`

The Nitter engine directory. Contains:
- `docker-compose.yml` -- Docker Compose configuration
- `nitter.conf` -- Nitter settings (HMAC key, port, etc.)
- `sessions.jsonl` -- Symlink to `~/.xpert/sessions.jsonl`

If you ever need to tweak Nitter settings, that is the file to edit.

---

## Contributing

Xpert is open source. Contributions are welcome.

**Report a bug:** Open an issue on GitHub with the error message, your command, and your setup.

**Contribute code:**

```bash
# 1. Fork and clone the repo
git clone https://github.com/gargtakesover/xpert-lib.git
cd xpert-lib

# 2. Create a feature branch
git checkout -b feature/my-feature

# 3. Install dev dependencies
pip install -e ".[dev]"

# 4. Run tests (unit tests only -- no live Nitter required)
python -m pytest tests/ -v --tb=short -m "not integration"

# 5. Run with live Nitter tests
RUN_LIVE_TESTS=1 python -m pytest tests/ -v --tb=short

# 6. Format and type-check
black src/
mypy src/

# 7. Commit and push
git add -A && git commit -m "feat: add my feature"
git push origin feature/my-feature

# 8. Open a PR
gh pr create
```

**Release process (maintainers):**
1. Update version in `pyproject.toml`
2. Tag: `git tag v1.x.x && git push --tags`
3. GitHub Actions builds and publishes to PyPI automatically

---

## Links

| Resource | URL |
|----------|-----|
| GitHub (library) | https://github.com/gargtakesover/xpert-lib |
| PyPI | https://pypi.org/project/xpert |
| Nitter | https://github.com/zedeus/nitter |

---

## License

MIT License. See `pyproject.toml` for details.
