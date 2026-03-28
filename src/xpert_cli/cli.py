"""
Xpert CLI - Premium command line interface for Twitter/X data access.

Usage:
    xpert install                  Download and start Nitter (first-time setup)
    xpert configure                Configure Twitter session tokens
    xpert user <username>          Get user profile and recent tweets
    xpert tweet <url>              Scrape a single tweet by URL
    xpert search <query>           Search tweets by query
    xpert timeline <username>       Get user timeline
    xpert thread <url>             Unroll a thread by tweet URL
    xpert cookies                  Manage session tokens
    xpert status                   Check xpert status and connectivity
    xpert setup                    First-time setup wizard
"""

import sys
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

# Force UTF-8 output on Windows to prevent charmap errors with Unicode characters
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass  # Python < 3.7: no reconfigure, ignore

import click

try:
    from importlib.metadata import version as _get_pkg_version
    _VERSION = _get_pkg_version("xpert")
except Exception:
    _VERSION = "1.0.0"

try:
    from xpert import Xpert, Tweet, User, XpertError, RateLimitError, NotFoundError
    from xpert import get_user, get_timeline, search as xpert_search, get_tweet, get_thread
    from xpert import search_users as xpert_search_users
    from xpert import cookies as cookies_module
    from xpert.config import NITTER_INSTANCES, ENGINE_DIR, SESSIONS_FILE, PACKAGE_DIR, BUNDLED_ENGINE_DIR, MAX_QUERY_LENGTH, LOG_FILE
    from xpert.scraper import check_nitter_health
    from xpert.exporters import tweets_to_format, tweets_to_csv, tweets_to_json, users_to_format, _clean_dict, _flatten_user
    MODULES_OK = True
except ImportError as e:
    Xpert = Tweet = User = None
    XpertError = RateLimitError = NotFoundError = Exception
    get_user = get_timeline = search = get_tweet = get_thread = search_users = None
    cookies_module = None
    check_nitter_health = None
    ENGINE_DIR = None
    SESSIONS_FILE = None
    PACKAGE_DIR = None
    BUNDLED_ENGINE_DIR = None
    NITTER_INSTANCES = []
    MAX_QUERY_LENGTH = 500
    LOG_FILE = Path("/dev/null")
    MODULES_OK = False
    MODULE_ERROR = str(e)


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"


def ok(text): return f"{C.GREEN}{C.BOLD}{text}{C.RESET}"
def err(text): return f"{C.RED}{C.BOLD}{text}{C.RESET}"
def warn(text): return f"{C.YELLOW}{text}{C.RESET}"
def info(text): return f"{C.CYAN}{text}{C.RESET}"
def hdr(text): return f"{C.BOLD}{C.BLUE}{text}{C.RESET}"
def dim(text): return f"{C.DIM}{text}{C.RESET}"


# ---------------------------------------------------------------------------
# Nitter auto-restart
# ---------------------------------------------------------------------------

def _ensure_proxy_config():
    """Ensure nitter.conf proxy matches XPERT_PROXY env var."""
    from xpert.config import DEFAULT_PROXY, ENGINE_DIR
    if not ENGINE_DIR:
        return
    
    nitter_conf = Path(ENGINE_DIR) / "nitter.conf"
    if not nitter_conf.exists() or DEFAULT_PROXY is None:
        return

    try:
        content = nitter_conf.read_text(encoding="utf-8")
        lines = content.splitlines()
        changed = False
        new_lines = []
        for line in lines:
            if line.strip().startswith("proxy") and not line.strip().startswith("proxyAuth"):
                # Handle `proxy = ""` or `proxy = "http..."`
                try:
                    current_proxy = line.split('=', 1)[1].strip().strip('"')
                    if current_proxy != DEFAULT_PROXY:
                        new_lines.append(f'proxy = "{DEFAULT_PROXY}"')
                        changed = True
                    else:
                        new_lines.append(line)
                except Exception:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        if changed:
            click.echo(info(f"Applying new proxy configuration..."), err=True)
            nitter_conf.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            click.echo(warn("Restarting Nitter to apply proxy changes..."), err=True)
            subprocess.run(["docker", "compose", "restart"], cwd=str(ENGINE_DIR), capture_output=True)
            time.sleep(2)
    except Exception as e:
        click.echo(err(f"Failed to update proxy config: {e}"), err=True)

def ensure_nitter_running():
    """Check Nitter health and auto-restart if needed."""
    if not MODULES_OK or check_nitter_health is None:
        return

    _ensure_proxy_config()

    if not cookies_module.has_cookies():
        click.echo(err("Configuration missing: Session cookies are not properly configured."))
        click.echo("Please run 'xpert configure' to provide valid Twitter tokens.")
        sys.exit(1)

    ok, msg = check_nitter_health(NITTER_INSTANCES[0])
    if ok:
        return

    auto_restart = os.environ.get("XPERT_AUTO_RESTART", "").lower() not in ("0", "false", "no")
    if not auto_restart:
        click.echo(warn(f"Nitter not running ({msg}). Set XPERT_AUTO_RESTART=1 to enable auto-restart."))
        sys.exit(1)

    click.echo(warn(f"Nitter not running ({msg}), attempting auto-restart..."))

    # Try to restart Nitter via docker compose (using bundled engine/)
    if ENGINE_DIR and os.path.isdir(ENGINE_DIR):
        # Ensure sessions symlink exists for Docker mount
        engine_sessions = ENGINE_DIR / "sessions.jsonl"
        if SESSIONS_FILE.exists() and not engine_sessions.exists():
            try:
                engine_sessions.symlink_to(SESSIONS_FILE)
            except OSError:
                pass

        try:
            result = subprocess.run(
                ["docker", "compose", "up", "-d"],
                cwd=str(ENGINE_DIR),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                click.echo(info("Nitter container started, waiting..."), err=True)
                time.sleep(3)
                # Verify it came up
                ok2, msg2 = check_nitter_health(NITTER_INSTANCES[0])
                if ok2:
                    click.echo(ok("Nitter is now running!"))
                    return
                click.echo(warn(f"Nitter started but not responding yet: {msg2}"))
                if "disconnected" in msg2.lower() or "refused" in msg2.lower():
                    click.echo(err("\n⚠ Nitter crashed immediately after starting."))
                    click.echo(warn("This is a known issue: Nitter expects OAuth 1.0 tokens (oauth_token)."))
                    click.echo(warn("Please check your session configuration in ~/.xpert/sessions.jsonl."))
            else:
                click.echo(err(f"Failed to start Nitter: {result.stderr}"))
        except subprocess.TimeoutExpired:
            click.echo(err("Nitter restart timed out"))
        except Exception as e:
            click.echo(err(f"Error restarting Nitter: {e}"))
    else:
        click.echo(err(f"Engine directory not found: {ENGINE_DIR}"))
        click.echo(err("Run 'xpert install' first to download and start Nitter."))


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def format_tweet(tweet: Tweet, index: int = 0) -> str:
    """Format a Tweet for terminal display."""
    lines = []
    lines.append(hdr(f"@{tweet.author}") + (f" · {ok('Pinned')}" if tweet.is_pinned else ""))
    lines.append(tweet.text)

    stats = []
    if tweet.likes: stats.append(f"❤ {tweet.likes:,}")
    if tweet.retweets: stats.append(f"🔁 {tweet.retweets:,}")
    if tweet.replies: stats.append(f"💬 {tweet.replies:,}")
    if tweet.views: stats.append(f"👁 {tweet.views:,}")
    if stats:
        lines.append(dim(" | ".join(stats)))

    if tweet.images:
        lines.append(dim(f"[{len(tweet.images)} image(s)]"))
    if tweet.videos:
        lines.append(dim(f"[Video: {tweet.videos[0].get('thumbnail', 'available')}]"))

    if tweet.is_thread:
        lines.append(info(f"🧵 Thread #{tweet.thread_position}/{tweet.thread_length}"))

    lines.append(info(tweet.url))
    return "\n".join(lines)


def format_user(user: User) -> str:
    """Format a User profile for terminal display."""
    lines = []
    verified = ok(" ✓") if user.verified else ""
    lines.append(hdr(f"@{user.username}") + verified)
    lines.append(f"Name: {user.display_name}")
    if user.bio:
        lines.append(f"Bio: {user.bio}")
    lines.append(f"Followers: {user.followers:,}  |  Following: {user.following:,}  |  Tweets: {user.tweets:,}")
    if user.joined:
        lines.append(f"Joined: {user.joined}")
    lines.append(info(user.url))
    return "\n".join(lines)


def handle_error(error: Exception, context: str = ""):
    """Print friendly error and exit. Logs to ~/.xpert/xpert.log."""
    logging.error("%s%s", f"[{context}] " if context else "", error)
    if isinstance(error, RateLimitError):
        click.echo(err(f"Rate limited: {error}"), err=True)
        click.echo(warn("Please wait a moment and try again."))
    elif isinstance(error, NotFoundError):
        click.echo(err(f"Not found: {error}"), err=True)
    elif isinstance(error, ConnectionError):
        click.echo(err("Nitter connection failed:"), err=True)
        click.echo("  %s" % dim(str(error).strip()), err=True)
        click.echo("")
        click.echo(warn("Troubleshooting:"), err=True)
        click.echo("  %s xpert doctor        # Run full health check" % info("→"), err=True)
        click.echo("  %s xpert status        # Check connectivity" % info("→"), err=True)
        click.echo("  %s xpert install       # Start/restart Nitter" % info("→"), err=True)
        sys.exit(1)
    elif isinstance(error, XpertError):
        click.echo(err(f"Error: {error}"), err=True)
    else:
        click.echo(err(f"Unexpected error: {error}"), err=True)
    sys.exit(1)



def _check_docker():
    import shutil, subprocess, sys
    if not shutil.which("docker"):
        click.echo(err("\n\u26A0 Docker is not installed!\nPlease download Docker Desktop: https://docker.com"), err=True)
        sys.exit(1)
    try:
        res = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        if res.returncode != 0:
            click.echo(err("\n\u26A0 Docker is installed but not running in the background!\nPlease open your Docker Desktop app first."), err=True)
            sys.exit(1)
    except Exception:
        click.echo(err("\n\u26A0 Docker is installed but not running in the background!\nPlease open your Docker Desktop app first."), err=True)
        sys.exit(1)

def _safe_output_path(path: str) -> Path:
    """Resolve output path and guard against path traversal."""
    resolved = Path(path).resolve()
    # Ensure path is within current working directory tree
    cwd = Path.cwd()
    try:
        resolved.relative_to(cwd)
    except ValueError:
        raise click.BadParameter(f"Output path must be within current directory ({cwd})")
    return resolved


def output_result(data, fmt: str, output: Optional[str], full_data: bool = False):
    """Output data in requested format."""
    try:
        if fmt == "json":
            if isinstance(data, list):
                out = json.dumps([_tweet_to_dict(t, full_data) for t in data], indent=2, ensure_ascii=False)
            elif isinstance(data, dict) and "profile" in data:
                composite = {
                    "profile": _user_to_dict(data["profile"], full_data),
                    "tweets": [_tweet_to_dict(t, full_data) for t in data.get("tweets", [])]
                }
                out = json.dumps(composite, indent=2, ensure_ascii=False)
            else:
                out = json.dumps(_user_to_dict(data, full_data), indent=2, ensure_ascii=False)
            if output:
                safe_path = _safe_output_path(output)
                with open(safe_path, "w", encoding="utf-8") as f:
                    f.write(out)
                click.echo(ok(f"Saved to {safe_path}"))
            else:
                click.echo(out)
        else:
            if not output:
                output = click.prompt("Output file path", type=str)
            safe_path = _safe_output_path(output)
            if isinstance(data, list):
                tweets_to_format(data, fmt, str(safe_path), full_data)
            elif isinstance(data, dict) and "profile" in data:
                # Handle user profile dict (from {"profile": User, "tweets": [...]})
                profile_dict = _user_to_dict(data["profile"], full_data)
                users_to_format([profile_dict], fmt, str(safe_path), full_data)
            else:
                # Single user object
                user_dict = _user_to_dict(data, full_data)
                users_to_format([user_dict], fmt, str(safe_path), full_data)
            click.echo(ok(f"Saved to {safe_path}"))
    except ValueError as e:
        raise click.ClickException(f"Failed to export data: {e}")


def _user_to_dict(u: User, full_data: bool = False) -> dict:
    """Alias for exporters._flatten_user to avoid duplication."""
    return _flatten_user(u, full_data)


def _tweet_to_dict(t: Tweet, full_data: bool = False) -> dict:
    d = {
        "id": t.id, "url": t.url, "author": t.author,
        "author_display": t.author_display, "text": t.text,
        "created_at": t.created_at, "likes": t.likes, "retweets": t.retweets,
        "replies": t.replies, "views": t.views, "content_type": t.content_type,
        "is_reply": t.is_reply, "is_retweet": t.is_retweet, "is_pinned": t.is_pinned,
        "is_thread": t.is_thread, "thread_position": t.thread_position,
        "thread_length": t.thread_length, "images": t.images,
        "is_edited": t.is_edited,
        "has_community_note": t.has_community_note,
        "community_note": t.community_note,
    }
    return _clean_dict(d, full_data)


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(version=_VERSION, prog_name="xpert")
def main():
    """Xpert - Access X data without the API."""
    # Structured logging — write to ~/.xpert/xpert.log
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=str(LOG_FILE),
            level=logging.WARNING,
            format="%(asctime)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    except Exception:
        # Logging is best-effort — don't fail the command if log file is unwritable
        pass


# ---------------------------------------------------------------------------
# configure
# ---------------------------------------------------------------------------

@main.command()
@click.option("--account", "-a", help="Account ID/username label for this session")
def configure(account: Optional[str]):
    """Configure Twitter session tokens (auth_token + ct0)."""
    if not MODULES_OK:
        click.echo(err(f"Module error: {MODULE_ERROR}"), err=True)
        sys.exit(1)

    click.echo(hdr("Configure Xpert Twitter Session"), err=True)
    click.echo(f"Sessions file: {dim(str(SESSIONS_FILE))}\n")

    # Show existing accounts if any
    existing_accounts = cookies_module.get_all_accounts()
    if existing_accounts:
        click.echo(info("Existing accounts:"), err=True)
        for acct in existing_accounts:
            click.echo(f"  {ok('●')} @{acct['username']} (id: {acct['id']})")
        click.echo("")

    click.echo(dim("Get tokens from twitter.com -> DevTools (F12) -> Application -> Cookies\n"))

    click.echo(info("Steps:"), err=True)
    click.echo("  1. Open twitter.com in your browser")
    click.echo("  2. Open Developer Tools (F12)")
    click.echo("  3. Go to Application > Cookies > twitter.com")
    click.echo("  4. Find 'auth_token' and 'ct0' values")
    click.echo("  5. Paste them below\n")

    token = click.prompt("Enter auth_token", type=str, hide_input=False)
    ct0 = click.prompt("Enter ct0", type=str, hide_input=False)
    username = click.prompt("Enter your Twitter username (optional)", type=str, default=account or "", show_default=False)
    if not username:
        username = account or ""

    try:
        cookies_module.save_cookies(token, ct0, username=username, account_id=username)
        click.echo(f"\n{ok('Session tokens saved!')}")

        valid, msg = cookies_module.validate_cookies(token, ct0)
        if valid:
            click.echo(ok(msg))
        else:
            click.echo(warn(f"Warning: {msg}"))

        click.echo(f"\n{info('Next steps:')}", err=True)
        click.echo(f"  {info('xpert install')}   # Start Nitter (first time only)", err=True)
        click.echo(f"  {info('xpert search hello')}   # Test it out", err=True)
    except cookies_module.CookieError as e:
        click.echo(err(f"Failed: {e}"), err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# stop
# ---------------------------------------------------------------------------

@main.command()
def stop():
    """Stop the background xpert engine."""
    if not MODULES_OK:
        click.echo(err("Module error"), err=True)
        sys.exit(1)
        
    engine_dir = Path(ENGINE_DIR) if ENGINE_DIR else None
    if not engine_dir or not engine_dir.exists():
        click.echo(err("Engine not found. Run 'xpert install' first."), err=True)
        sys.exit(1)
        
    click.echo(info("Stopping background Xpert engine..."), err=True)
    try:
        result = subprocess.run(
            ["docker", "compose", "stop"],
            cwd=str(engine_dir),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            click.echo(ok("Engine properly stopped. It will auto-start next time you scan!"), err=True)
        else:
            click.echo(err(f"Failed to stop engine: {result.stderr}"), err=True)
    except Exception as e:
        click.echo(err(f"Error stopping Docker: {e}"), err=True)


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------

@main.command()
@click.option("--cores", is_flag=True, help="Show available CPU cores")
@click.option("--force", is_flag=True, help="Re-copy bundled engine (use after upgrading xpert)")
def install(cores: bool, force: bool):
    """Download and start Nitter via Docker (first-time setup)."""
    if not MODULES_OK:
        click.echo(err(f"Module error: {MODULE_ERROR}"), err=True)
        sys.exit(1)

    if cores:
        try:
            import os
            c = len(os.sched_getaffinity(0))
            click.echo(f"Available CPU cores: {ok(str(c))}")
        except Exception:
            import multiprocessing
            click.echo(f"CPU cores: {ok(str(multiprocessing.cpu_count()))}")
        return

    click.echo(hdr("Xpert Install"), err=True)
    # Normalize ENGINE_DIR to Path for consistent operations
    engine_dir = ENGINE_DIR if isinstance(ENGINE_DIR, Path) else Path(ENGINE_DIR)
    click.echo(f"Engine directory: {dim(str(engine_dir))}\n")

    try:
        _check_docker()
    except Exception as e:
        click.echo(err(f"Error checking Docker: {e}"))
        sys.exit(1)

    # Check Docker daemon health (storage driver, etc.)
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.Driver}}"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            click.echo(err("Docker daemon is not responding."))
            click.echo(f"  {err(result.stderr.strip() or 'Run: sudo systemctl start docker')}")
            sys.exit(1)
        driver = result.stdout.strip()
        click.echo(f"{ok('●')} Storage driver: {driver}")
        if driver == "overlay2":
            click.echo(warn("  Note: overlay2 is recommended. Some environments with overlayfs may have issues."))
    except FileNotFoundError:
        pass  # docker exists, this shouldn't fail

    # Check if docker-compose is available
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            # Try docker-compose (legacy)
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        if result.returncode == 0:
            click.echo(f"{ok('●')} Docker Compose: {result.stdout.strip()}")
    except FileNotFoundError:
        click.echo(err("Docker Compose is not installed."))
        sys.exit(1)

    # Check if sessions are configured at the value level
    if not cookies_module.has_cookies():
        click.echo(err("\n⚠ Configuration missing: No valid session tokens found."))
        click.echo("Run 'xpert configure' first to add your Twitter auth tokens.\n")
        sys.exit(1)

    # Copy engine files to user directory if running from pip-installed location
    bundled_engine = BUNDLED_ENGINE_DIR
    user_engine = engine_dir
    if bundled_engine.exists() and str(bundled_engine) != str(user_engine):
        if not user_engine.exists() or force:
            click.echo(info(f"\nInstalling engine to {user_engine}..."), err=True)
            import shutil
            try:
                if force and user_engine.exists():
                    shutil.rmtree(user_engine)
                shutil.copytree(bundled_engine, user_engine)
                click.echo(ok("Engine installed."))
            except Exception as e:
                click.echo(err(f"Failed to install engine: {e}"))
                sys.exit(1)

    # Generate random HMAC key if still using placeholder or empty
    nitter_conf = engine_dir / "nitter.conf"
    if nitter_conf.exists():
        import re
        conf_content = nitter_conf.read_text()
        placeholder = "xpert-secret-key-change-in-production"
        # Check for placeholder or empty key using regex for robustness
        needs_key = (
            placeholder in conf_content or
            re.search(r'hmacKey\s*=\s*""', conf_content)
        )
        if needs_key:
            import secrets
            new_key = secrets.token_hex(32)
            conf_content = re.sub(
                r'hmacKey\s*=\s*".*"',
                f'hmacKey = "{new_key}"',
                conf_content,
            )
            nitter_conf.write_text(conf_content)
            click.echo(ok("Generated secure HMAC key."))

    # Symlink sessions.jsonl into engine dir for Docker mount
    # Docker needs sessions.jsonl next to nitter.conf for the volume mount
    engine_sessions = engine_dir / "sessions.jsonl"
    if SESSIONS_FILE.exists() and not engine_sessions.exists():
        try:
            engine_sessions.symlink_to(SESSIONS_FILE)
        except OSError:
            pass  # Fallback: docker will use its own sessions if file missing

    # Start Nitter
    click.echo(info("\nStarting Nitter and Redis containers..."), err=True)
    try:
        result = subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd=str(engine_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            click.echo(err(f"Failed to start containers: {result.stderr}"))
            sys.exit(1)

        click.echo(info("Waiting for Nitter to be ready..."), err=True)
        time.sleep(5)

        # Check if Nitter is healthy
        ok_n, msg = check_nitter_health(NITTER_INSTANCES[0])
        if ok_n:
            click.echo(ok(f"\n✓ Nitter is running at {NITTER_INSTANCES[0]}"))
            click.echo(f"\n{ok('Installation complete!')}")
            click.echo(f"\n{info('Next steps:')}", err=True)
            click.echo(f"  {info('xpert search hello')}   # Try your first search", err=True)
        else:
            click.echo(warn(f"\n⚠ Nitter started but not responding: {msg}"))
            click.echo("Wait a few seconds and run 'xpert status' to check again.")

    except subprocess.TimeoutExpired:
        click.echo(err("Timeout starting containers."))
        sys.exit(1)
    except Exception as e:
        click.echo(err(f"Error: {e}"))
        sys.exit(1)


# ---------------------------------------------------------------------------
# cookies
# ---------------------------------------------------------------------------

@main.command()
@click.option("--token", help="auth_token session token")
@click.option("--ct0", help="ct0 session token")
@click.option("--clear", is_flag=True, help="Clear ALL saved sessions")
@click.option("--account", "-a", help="Clear only a specific account")
def cookies(token: Optional[str], ct0: Optional[str], clear: bool, account: Optional[str]):
    """Manage Twitter session tokens for Nitter (multi-account supported)."""
    if not MODULES_OK:
        click.echo(err("Module error"), err=True)
        sys.exit(1)

    if clear:
        if account:
            cookies_module.clear_cookies(account)
            click.echo(ok(f"Account '{account}' removed."))
        else:
            cookies_module.clear_cookies()
            click.echo(ok("All sessions cleared."))
        return

    if token and ct0:
        username = account or ""
        try:
            cookies_module.save_cookies(token, ct0, username=username, account_id=username)
            click.echo(ok("Session tokens saved!"))
        except cookies_module.CookieError as e:
            click.echo(err(f"Error: {e}"), err=True)
        return

    # Show status for all accounts
    status = cookies_module.get_cookies_status()
    click.echo(hdr("Session Status"), err=True)
    click.echo(f"File: {dim(status['sessions_file'])}")
    if not status["configured"]:
        click.echo(f"{warn('○')} Not configured")
        click.echo(f"\n  Run: {info('xpert configure')}", err=True)
        click.echo(f"  Or:  {info('xpert cookies --token TOKEN --ct0 CT0')}", err=True)
        return

    click.echo(f"{ok('●')} {status['account_count']} account(s) configured:")
    for acct in status.get("accounts", []):
        click.echo(f"  {ok('●')} @{acct['username']} (id: {acct['id']})")
        click.echo(f"     auth_token: {acct['token_prefix']}...")
        click.echo(f"     ct0: {acct['ct0_prefix']}...")



# ---------------------------------------------------------------------------
# user
# ---------------------------------------------------------------------------

@main.command()
@click.argument("username")
@click.option("--limit", "-n", default=10, help="Number of tweets")
@click.option("--format", "-f", type=click.Choice(["json", "csv", "excel", "markdown"]), default="json", help="Output format")
@click.option("--output", "-o", help="Output file")
@click.option("--delay", type=float, default=None, help="Scraping delay in seconds")
@click.option("--full-data", is_flag=True, help="Include empty fields in JSON/CSV")
def user(username: str, limit: int, format: str, output: Optional[str], delay: Optional[float], full_data: bool):
    """Get user profile and recent tweets."""
    if limit > 800:
        click.echo(warn("Warning: Nitter enforces a maximum of 800 results per query. Clamping limit to 800."), err=True)
        limit = 800
    if not MODULES_OK:
        click.echo(err("Module error"), err=True)
        sys.exit(1)

    ensure_nitter_running()
    if delay is not None:
        from xpert import config
        config.CURRENT_DELAY = delay
    username = username.lstrip("@")
    click.echo(f"Fetching @{username}...", err=True)

    try:
        profile = get_user(username)
        tweets = get_timeline(username, limit=limit)

        click.echo(f"\n{format_user(profile)}\n")

        if tweets:
            click.echo(hdr(f"Recent Tweets ({len(tweets)}):"), err=True)
            for t in tweets[:5]:
                click.echo(f"\n---")
                click.echo(format_tweet(t))
            if len(tweets) > 5:
                click.echo(dim(f"\n... and {len(tweets) - 5} more"))

        output_result({"profile": profile, "tweets": tweets}, format, output, full_data)

    except Exception as e:
        handle_error(e, f"user @{username}")


# ---------------------------------------------------------------------------
# tweet
# ---------------------------------------------------------------------------

@main.command()
@click.argument("url")
@click.option("--format", "-f", type=click.Choice(["json", "csv", "excel", "markdown"]), default="json")
@click.option("--output", "-o", help="Output file")
@click.option("--delay", type=float, default=None, help="Scraping delay in seconds")
@click.option("--full-data", is_flag=True, help="Include empty fields in JSON/CSV")
def tweet(url: str, format: str, output: Optional[str], delay: Optional[float], full_data: bool):
    """Scrape a single tweet by URL."""
    if not MODULES_OK:
        click.echo(err("Module error"), err=True)
        sys.exit(1)

    ensure_nitter_running()
    if delay is not None:
        from xpert import config
        config.CURRENT_DELAY = delay
    click.echo(f"Fetching tweet...", err=True)

    try:
        t = get_tweet(url)
        click.echo(f"\n{format_tweet(t)}\n")
        output_result([t], format, output, full_data)
    except Exception as e:
        handle_error(e, "tweet URL")


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

@main.command()
@click.argument("query")
@click.option("--limit", "-n", default=10, help="Number of results")
@click.option("--min-faves", type=int, help="Minimum likes")
@click.option("--min-retweets", type=int, help="Minimum retweets")
@click.option("--min-replies", type=int, help="Minimum replies")
@click.option("--min-engagement", type=int, help="Minimum total engagement (likes+retweets+replies)")
@click.option("--since", help="Filter since (YYYY-MM-DD)")
@click.option("--until", help="Filter until (YYYY-MM-DD)")
@click.option("--near", help="Geo filter (city,country)")
@click.option("--verified-only", is_flag=True, help="Only verified users")
@click.option("--has-engagement", is_flag=True, help="Exclude zero-engagement tweets")
@click.option("--time-within", type=click.Choice(["25m", "6h", "24h", "7d"]), help="Relative time filter")
@click.option("--filters", help="Include only: media,images,videos,links (comma-separated)")
@click.option("--excludes", help="Exclude: media,videos (comma-separated)")
@click.option("--query-type", type=click.Choice(["live", "top", "latest"]), default="live", help="Sort order")
@click.option("--format", "-f", type=click.Choice(["json", "csv", "excel", "markdown"]), default="json")
@click.option("--output", "-o", help="Output file")
@click.option("--delay", type=float, default=None, help="Scraping delay in seconds")
@click.option("--full-data", is_flag=True, help="Include empty fields in JSON/CSV")
def search(
    query: str,
    limit: int,
    min_faves: Optional[int],
    min_retweets: Optional[int],
    min_replies: Optional[int],
    min_engagement: Optional[int],
    since: Optional[str],
    until: Optional[str],
    near: Optional[str],
    verified_only: bool,
    has_engagement: bool,
    time_within: Optional[str],
    filters: Optional[str],
    excludes: Optional[str],
    query_type: str,
    format: str,
    output: Optional[str],
    delay: Optional[float],
    full_data: bool,
):
    """Search tweets by query with full filter support."""
    if limit > 800:
        click.echo(warn("Warning: Nitter enforces a maximum of 800 results per query. Clamping limit to 800."), err=True)
        limit = 800
    if not MODULES_OK:
        click.echo(err("Module error"), err=True)
        sys.exit(1)

    ensure_nitter_running()
    if delay is not None:
        from xpert import config
        config.CURRENT_DELAY = delay

    # Validate date filters
    from datetime import datetime
    if since:
        try:
            datetime.fromisoformat(since)
        except ValueError:
            click.echo(err(f"Invalid --since date: '{since}'. Use YYYY-MM-DD format."), err=True)
            sys.exit(1)
    if until:
        try:
            datetime.fromisoformat(until)
        except ValueError:
            click.echo(err(f"Invalid --until date: '{until}'. Use YYYY-MM-DD format."), err=True)
            sys.exit(1)
    if since and until:
        try:
            if datetime.fromisoformat(since) > datetime.fromisoformat(until):
                click.echo(err(f"--since ({since}) must be before --until ({until})."), err=True)
                sys.exit(1)
        except ValueError:
            pass  # Already handled above

    if len(query) > MAX_QUERY_LENGTH:
        click.echo(err(f"Query too long ({len(query)} chars). Maximum is {MAX_QUERY_LENGTH}."), err=True)
        sys.exit(1)

    click.echo(f'Searching for "{query}"...', err=True)

    try:
        tweets = xpert_search(
            query,
            limit=limit,
            min_faves=min_faves,
            min_retweets=min_retweets,
            min_replies=min_replies,
            min_engagement=min_engagement,
            since=since,
            until=until,
            near=near,
            verified_only=verified_only,
            has_engagement=has_engagement,
            time_within=time_within,
            filters=filters,
            excludes=excludes,
            query_type=query_type,
        )

        if not tweets:
            click.echo(warn(f"No results for: {query}"))
            if min_faves or min_retweets or min_replies:
                click.echo(info("Try removing engagement filters"), err=True)
            return

        click.echo(hdr(f"Found {len(tweets)} tweets:"), err=True)
        for i, t in enumerate(tweets[:10], 1):
            click.echo(f"\n{i}. {format_tweet(t)}")
        if len(tweets) > 10:
            click.echo(dim(f"\n... and {len(tweets) - 10} more"))

        output_result(tweets, format, output, full_data)

    except Exception as e:
        handle_error(e, f"search '{query}'")


# ---------------------------------------------------------------------------
# search-users
# ---------------------------------------------------------------------------

@main.command()
@click.argument("query")
@click.option("--limit", "-n", default=10, help="Number of results")
@click.option("--format", "-f", type=click.Choice(["json"]), default="json")
@click.option("--output", "-o", help="Output file")
@click.option("--delay", type=float, default=None, help="Scraping delay in seconds")
@click.option("--full-data", is_flag=True, help="Include empty fields in JSON/CSV")
def search_users(query: str, limit: int, format: str, output: Optional[str], delay: Optional[float], full_data: bool):
    """Search for users by query."""
    if limit > 800:
        click.echo(warn("Warning: Nitter enforces a maximum of 800 results per query. Clamping limit to 800."), err=True)
        limit = 800
    if not MODULES_OK:
        click.echo(err("Module error"), err=True)
        sys.exit(1)

    ensure_nitter_running()
    if delay is not None:
        from xpert import config
        config.CURRENT_DELAY = delay
    click.echo(f'Searching for users: "{query}"...', err=True)

    try:
        users = xpert_search_users(query, limit=limit)

        if not users:
            click.echo(warn(f"No users found for: {query}"))
            return

        click.echo(hdr(f"Found {len(users)} users:"), err=True)
        for i, u in enumerate(users[:20], 1):
            verified = ok(" ✓") if u.verified else ""
            click.echo(f"\n{i}. {hdr('@' + u.username)}{verified}", err=True)
            click.echo(f"   {u.display_name}")
            if u.bio:
                bio_short = u.bio[:80] + "..." if len(u.bio) > 80 else u.bio
                click.echo(f"   {dim(bio_short)}")
            click.echo(f"   Followers: {u.followers:,} | Following: {u.following:,}")

        if len(users) > 20:
            click.echo(dim(f"\n... and {len(users) - 20} more"))

        # Output as JSON
        if output:
            safe_path = _safe_output_path(output)
            with open(safe_path, "w", encoding="utf-8") as f:
                json.dump([_user_to_dict(u, full_data) for u in users], f, indent=2, ensure_ascii=False)
            click.echo(ok(f"Saved to {safe_path}"))
        else:
            click.echo(json.dumps([_user_to_dict(u, full_data) for u in users], indent=2, ensure_ascii=False))

    except Exception as e:
        handle_error(e, f"search-users '{query}'")


# ---------------------------------------------------------------------------
# timeline
# ---------------------------------------------------------------------------

@main.command()
@click.argument("username")
@click.option("--limit", "-n", default=10, help="Number of tweets")
@click.option("--format", "-f", type=click.Choice(["json", "csv", "excel", "markdown"]), default="json")
@click.option("--output", "-o", help="Output file")
@click.option("--delay", type=float, default=None, help="Scraping delay in seconds")
@click.option("--full-data", is_flag=True, help="Include empty fields in JSON/CSV")
def timeline(username: str, limit: int, format: str, output: Optional[str], delay: Optional[float], full_data: bool):
    """Get user timeline (recent tweets)."""
    if limit > 800:
        click.echo(warn("Warning: Nitter enforces a maximum of 800 results per query. Clamping limit to 800."), err=True)
        limit = 800
    if not MODULES_OK:
        click.echo(err("Module error"), err=True)
        sys.exit(1)

    ensure_nitter_running()
    if delay is not None:
        from xpert import config
        config.CURRENT_DELAY = delay
    username = username.lstrip("@")
    click.echo(f"Fetching timeline for @{username}...", err=True)

    try:
        tweets = get_timeline(username, limit=limit)

        if not tweets:
            click.echo(warn(f"No tweets found for @{username}"))
            return

        click.echo(hdr(f"@{username}'s Timeline ({len(tweets)} tweets):"), err=True)
        for i, t in enumerate(tweets[:10], 1):
            click.echo(f"\n{i}. {format_tweet(t)}")
        if len(tweets) > 10:
            click.echo(dim(f"\n... and {len(tweets) - 10} more"))

        output_result(tweets, format, output, full_data)

    except Exception as e:
        handle_error(e, f"timeline @{username}")


# ---------------------------------------------------------------------------
# thread
# ---------------------------------------------------------------------------

@main.command()
@click.argument("url")
@click.option("--format", "-f", type=click.Choice(["json", "csv", "excel", "markdown"]), default="json")
@click.option("--output", "-o", help="Output file")
@click.option("--delay", type=float, default=None, help="Scraping delay in seconds")
@click.option("--full-data", is_flag=True, help="Include empty fields in JSON/CSV")
def thread(url: str, format: str, output: Optional[str], delay: Optional[float], full_data: bool):
    """Unroll/expand a thread by tweet URL."""
    if not MODULES_OK:
        click.echo(err("Module error"), err=True)
        sys.exit(1)

    ensure_nitter_running()
    if delay is not None:
        from xpert import config
        config.CURRENT_DELAY = delay
    click.echo("Fetching thread...", err=True)

    try:
        tweets = get_thread(url)

        if not tweets:
            click.echo(warn("No thread found"))
            return

        click.echo(hdr(f"Thread ({len(tweets)} tweets):"), err=True)
        for t in tweets:
            click.echo(f"\n{hdr(f'Tweet {t.thread_position}/{t.thread_length}')}", err=True)
            click.echo(format_tweet(t))

        output_result(tweets, format, output, full_data)

    except Exception as e:
        handle_error(e, f"thread {url}")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

@main.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed info")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--selectors", is_flag=True, help="Run CSS selector health check against live Nitter")
def status(verbose: bool, as_json: bool, selectors: bool):
    """Check xpert status, cookies, and Nitter connectivity."""
    if not MODULES_OK:
        if as_json:
            click.echo(json.dumps({"ok": False, "error": MODULE_ERROR}))
        else:
            click.echo(f"{err('✗')} Module error: {MODULE_ERROR}")
        sys.exit(1)

    # Collect status data
    status_cookies = cookies_module.get_cookies_status()
    nitter_statuses = []
    primary_ok = False
    for inst in NITTER_INSTANCES[:3]:
        ok_nitter, msg = check_nitter_health(inst)
        nitter_statuses.append({"url": inst, "ok": ok_nitter, "message": msg})
        if inst == NITTER_INSTANCES[0]:
            primary_ok = ok_nitter

    cookies_ok = status_cookies["configured"]
    ready = cookies_ok and primary_ok

    if as_json:
        output = {
            "ok": ready,
            "cookies_configured": cookies_ok,
            "nitter_primary_ok": primary_ok,
            "nitter_instances": nitter_statuses,
        }
        click.echo(json.dumps(output, indent=2))
        return

    click.echo(hdr("Xpert Status"), err=True)
    click.echo("")

    # Cookies
    click.echo(info("Authentication:"), err=True)
    if status_cookies["configured"]:
        click.echo(f"  {ok('●')} Cookies configured")
        click.echo(f"    auth_token: {status_cookies['token_prefix']}...")
        click.echo(f"    ct0: {status_cookies['ct0_prefix']}...")
    else:
        click.echo(f"  {warn('○')} Cookies not configured")
        click.echo(f"    Run: {info('xpert configure')}", err=True)

    click.echo("")

    # Nitter
    click.echo(info("Nitter Connectivity:"), err=True)
    for inst_data in nitter_statuses:
        if inst_data["ok"]:
            click.echo(f"  {ok('●')} {inst_data['url']}: {inst_data['message']}")
        else:
            click.echo(f"  {err('✗')} {inst_data['url']}: {inst_data['message']}")
            if "disconnected" in inst_data['message'].lower() or "refused" in inst_data['message'].lower():
                click.echo(warn("    ↳ Hint: Nitter is permanently crashing on startup."))
                click.echo(warn("      This happens when sessions.jsonl contains auth_token/ct0 web cookies"))
                click.echo(warn("      instead of the OAuth 1.0 (auth_token/ct0) format it expects."))
            if verbose:
                click.echo(err("  Troubleshooting:"))
                click.echo("    docker ps | grep nitter", err=True)
                click.echo(f"    cd {ENGINE_DIR} && docker compose up -d", err=True)

    click.echo("")

    if selectors:
        click.echo(hdr("Selector Health Check"), err=True)
        click.echo("Fetching test page (@BillGates profile)...", err=True)
        try:
            from xpert.scraper import check_selector_health_public
            health = check_selector_health_public(NITTER_INSTANCES[0])
            if not health:
                click.echo(err("Could not fetch test page"))
            else:
                click.echo(f"\n{'Selector':<30} {'Elements':>10}")
                click.echo("-" * 42)
                for name, count in sorted(health.items()):
                    if count == -1:
                        click.echo(f"  {err(name):<30} {'ERROR':>10}")
                    elif count == 0:
                        click.echo(f"  {warn(name):<30} {'0':>10}")
                    else:
                        click.echo(f"  {dim(name):<30} {count:>10}")
                degraded = [n for n, c in health.items() if c == 0]
                if degraded:
                    click.echo(warn(f"\n⚠ {len(degraded)} selectors returned 0 elements."))
                    click.echo(warn("Nitter HTML structure may have changed. Run 'xpert upgrade' to update."))
        except Exception as e:
            click.echo(err(f"Selector check failed: {e}"))
        click.echo("")

    if ready:
        click.echo(ok("Xpert is ready! Run 'xpert search hello' to test."))
    elif cookies_ok:
        click.echo(warn("Xpert needs Nitter running. Run 'xpert install' to start it."))
    elif primary_ok:
        click.echo(warn("Xpert needs session tokens. Run 'xpert configure' to add them."))
    else:
        click.echo(warn("Xpert needs setup. Run 'xpert setup' for guidance."))

    click.echo("")
    click.echo(dim("Tip: Run 'xpert doctor' for a comprehensive diagnostic including CSS selector health."))


# ---------------------------------------------------------------------------
# setup
# ---------------------------------------------------------------------------

@main.command()
def setup():
    """First-time setup wizard."""
    click.echo(hdr("Welcome to Xpert!"), err=True)
    click.echo("")
    click.echo("Let's get you set up to access X data from the command line.\n")

    # Python version
    click.echo(info("1. Python version:"), err=True)
    v = sys.version_info
    if v.major >= 3 and v.minor >= 9:
        click.echo(f"  {ok(f'Python {v.major}.{v.minor}.{v.micro} ✓')}")
    else:
        click.echo(f"  {warn(f'Python {v.major}.{v.minor} (recommended: 3.9+)')}")
    click.echo("")

    # Nitter
    click.echo(info("2. Nitter connectivity:"), err=True)
    if check_nitter_health:
        ok_n, msg = check_nitter_health(NITTER_INSTANCES[0])
        if ok_n:
            click.echo(f"  {ok('●')} Nitter running at {NITTER_INSTANCES[0]}")
        else:
            click.echo(f"  {err('✗')} Nitter not running: {msg}")
            click.echo(warn("\n  Start Nitter:"))
            click.echo("    xpert install")
    click.echo("")

    # Sessions
    click.echo(info("3. Twitter session tokens:"), err=True)
    if cookies_module and cookies_module.has_cookies():
        click.echo(f"  {ok('●')} Configured in sessions.jsonl")
    else:
        click.echo(f"  {warn('○')} Not configured")
        click.echo(f"\n  Run: {info('xpert configure')}", err=True)

    click.echo("")
    click.echo(hdr("Next steps:"), err=True)
    click.echo("  xpert install            # Start Nitter (first time only)")
    click.echo("  xpert configure          # Add Twitter session tokens")
    click.echo("  xpert search hello      # Try your first search")
    click.echo("")
    click.echo(ok("You're ready to use Xpert!"))


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------

@main.command(name="doctor")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed info")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def doctor(verbose: bool, as_json: bool):
    """Run comprehensive health check including CSS selector diagnostics.

    This is equivalent to 'xpert status --verbose --selectors' but
    provides a more prominent summary of potential issues.
    """
    if not MODULES_OK:
        if as_json:
            click.echo(json.dumps({"ok": False, "error": MODULE_ERROR}))
        else:
            click.echo("%s Module error: %s" % (err("✗"), MODULE_ERROR))
        sys.exit(1)

    # Run status check
    status_cookies = cookies_module.get_cookies_status()
    nitter_statuses = []
    primary_ok = False
    for inst in NITTER_INSTANCES[:3]:
        ok_nitter, msg = check_nitter_health(inst)
        nitter_statuses.append({"url": inst, "ok": ok_nitter, "message": msg})
        if inst == NITTER_INSTANCES[0]:
            primary_ok = ok_nitter

    cookies_ok = status_cookies["configured"]
    ready = cookies_ok and primary_ok

    if as_json:
        output = {
            "ok": ready,
            "cookies_configured": cookies_ok,
            "nitter_primary_ok": primary_ok,
            "nitter_instances": nitter_statuses,
        }
        click.echo(json.dumps(output, indent=2))
        return

    click.echo(hdr("Xpert Doctor"), err=True)
    click.echo("")

    # Overall status
    if ready:
        click.echo("%s All systems operational" % ok("✓"))
    else:
        click.echo("%s Issues detected" % warn("⚠"))
    click.echo("")

    # Cookies
    click.echo(info("Authentication:"), err=True)
    if status_cookies["configured"]:
        click.echo("  %s Cookies configured" % ok("●"))
    else:
        click.echo("  %s Cookies not configured - run 'xpert configure'" % warn("○"))

    # Nitter
    click.echo(info("Nitter Connectivity:"), err=True)
    for inst_data in nitter_statuses:
        if inst_data["ok"]:
            click.echo("  %s %s: %s" % (ok("●"), inst_data["url"], inst_data["message"]))
        else:
            click.echo("  %s %s: %s" % (err("✗"), inst_data["url"], inst_data["message"]))
            if "disconnected" in inst_data["message"].lower() or "refused" in inst_data["message"].lower():
                click.echo("    %s Nitter crashing on startup" % warn("↳"))

    # CSS Selector health
    click.echo("")
    click.echo(info("CSS Selector Health:"), err=True)
    try:
        from xpert.scraper import check_selector_health_public
        click.echo("  Fetching test page...", err=True)
        health = check_selector_health_public(NITTER_INSTANCES[0])
        if not health:
            click.echo("  %s Could not fetch test page" % err("✗"))
        else:
            degraded = [n for n, c in health.items() if c == 0]
            if not degraded:
                click.echo("  %s All selectors working" % ok("●"))
            else:
                click.echo("  %s %d selector(s) returning 0 elements" % (warn("⚠"), len(degraded)))
                if verbose:
                    for name in degraded[:10]:
                        click.echo("    - %s" % warn(name))
                    if len(degraded) > 10:
                        click.echo("    %s ... and %d more" % (dim("..."), len(degraded) - 10))
    except Exception as e:
        click.echo("  %s Selector check unavailable: %s" % (dim("?"), str(e)[:60]))

    click.echo("")
    if ready:
        click.echo(ok("Xpert is ready! Run 'xpert search hello' to test."))
    else:
        click.echo(warn("Run 'xpert status' for full troubleshooting details."))


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

@main.command()
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompts")
@click.confirmation_option(prompt="This will stop all containers, remove Docker images, delete ~/.xpert, and uninstall the xpert package. Continue?")
def uninstall(force: bool):
    """Completely remove xpert: stop Nitter, remove Docker images, config, and package."""
    if not MODULES_OK:
        click.echo(err(f"Module error: {MODULE_ERROR}"), err=True)
        sys.exit(1)

    click.echo(hdr("Xpert Uninstall"), err=True)

    # Step 1: Stop Nitter containers
    click.echo(info("Stopping Nitter containers..."), err=True)
    engine_dir = ENGINE_DIR if isinstance(ENGINE_DIR, Path) else Path(ENGINE_DIR)
    if engine_dir.exists():
        try:
            subprocess.run(
                ["docker", "compose", "down", "-v"],
                cwd=str(engine_dir),
                capture_output=True,
                text=True,
                timeout=60,
            )
            click.echo(ok("Containers stopped."))
        except subprocess.TimeoutExpired:
            click.echo(warn("Timeout stopping containers."))
        except Exception as e:
            click.echo(warn(f"Could not stop containers: {e}"))
    else:
        click.echo(dim("No engine directory found, skipping container stop."))

    # Step 2: Remove Nitter Docker images
    click.echo(info("Removing Nitter Docker image (zedeus/nitter)..."), err=True)
    try:
        img_result = subprocess.run(
            ["docker", "images", "-q", "zedeus/nitter"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        img_ids = img_result.stdout.strip().splitlines()
        if img_ids and img_ids[0]:
            subprocess.run(
                ["docker", "rmi", "-f"] + img_ids,
                capture_output=True,
                text=True,
                timeout=60,
            )
            click.echo(ok("Nitter image removed."))
        else:
            click.echo(dim("No Nitter image found."))
    except Exception as e:
        click.echo(warn(f"Could not remove Nitter image: {e}"))

    # Step 3: Remove config directory
    click.echo(info("Removing ~/.xpert config directory..."), err=True)
    config_dir = Path("~/.xpert").expanduser()
    if config_dir.exists():
        import shutil
        try:
            shutil.rmtree(config_dir)
            click.echo(ok(f"Removed {config_dir}"))
        except Exception as e:
            click.echo(warn(f"Could not remove config dir: {e}"))
    else:
        click.echo(dim("No config directory found."))

    # Step 4: Uninstall xpert package
    click.echo(info("Uninstalling xpert Python package..."), err=True)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "xpert", "-y"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            click.echo(ok("xpert package uninstalled."))
        else:
            click.echo(warn(f"pip uninstall returned: {result.stderr}"))
    except Exception as e:
        click.echo(warn(f"Could not uninstall package: {e}"))

    click.echo(f"\n{ok('Uninstall complete!')}")
    click.echo("To start fresh: pip install xpert && xpert install")


@main.command()
def upgrade():
    """Upgrade xpert package and Nitter Docker image to latest versions."""
    if not MODULES_OK:
        click.echo(err(f"Module error: {MODULE_ERROR}"), err=True)
        sys.exit(1)

    click.echo(hdr("Xpert Upgrade"), err=True)

    # Step 1: Upgrade xpert Python package via pip
    click.echo(info("Upgrading xpert package..."), err=True)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "xpert"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            click.echo(ok("xpert package upgraded."))
            if result.stdout:
                for line in result.stdout.splitlines()[-5:]:
                    click.echo(dim(f"  {line.strip()}"))
        else:
            click.echo(err(f"Failed to upgrade xpert: {result.stderr}"))
            sys.exit(1)
    except subprocess.TimeoutExpired:
        click.echo(err("Upgrade timed out."))
        sys.exit(1)
    except Exception as e:
        click.echo(err(f"Error upgrading xpert: {e}"))
        sys.exit(1)

    # Step 2: Pull latest Nitter Docker image
    click.echo(info("\nPulling latest Nitter Docker image..."), err=True)
    try:
        result = subprocess.run(
            ["docker", "pull", "zedeus/nitter:latest"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            click.echo(ok("Nitter image updated."))
        else:
            click.echo(warn(f"Docker pull failed (may be expected on some systems): {result.stderr}"))
    except subprocess.TimeoutExpired:
        click.echo(warn("Docker pull timed out. Nitter image may already be up to date."))
    except FileNotFoundError:
        click.echo(warn("Docker not found. Skipping Nitter image update."))
    except Exception as e:
        click.echo(warn(f"Error pulling Nitter image: {e}"))

    # Step 3: Re-copy bundled engine to ~/.xpert/engine if needed
    engine_dir = ENGINE_DIR if isinstance(ENGINE_DIR, Path) else Path(ENGINE_DIR)
    bundled_engine = PACKAGE_DIR / "engine"
    if bundled_engine.exists() and bundled_engine != engine_dir:
        click.echo(info("\nUpdating bundled engine..."), err=True)
        import shutil
        try:
            if engine_dir.exists():
                shutil.rmtree(engine_dir)
            shutil.copytree(bundled_engine, engine_dir)
            click.echo(ok("Bundled engine updated."))
        except Exception as e:
            click.echo(warn(f"Could not update bundled engine: {e}"))

    # Step 4: Restart Nitter with new image
    click.echo(info("\nRestarting Nitter containers..."), err=True)
    if engine_dir.exists():
        try:
            # Restart containers to use new image
            subprocess.run(
                ["docker", "compose", "up", "-d", "--force-recreate"],
                cwd=str(engine_dir),
                capture_output=True,
                timeout=60,
            )
            click.echo(ok("Nitter containers restarted."))
            time.sleep(3)

            # Verify health
            ok_n, msg = check_nitter_health(NITTER_INSTANCES[0])
            if ok_n:
                click.echo(ok(f"Nitter is running at {NITTER_INSTANCES[0]}"))
            else:
                click.echo(warn(f"Nitter restarted but not responding yet: {msg}"))
        except Exception as e:
            click.echo(warn(f"Could not restart Nitter: {e}"))
            click.echo(f"\nTo restart manually: {info('cd {engine_dir} && docker compose up -d')}", err=True)

    click.echo(f"\n{ok('Upgrade complete!')}")
    click.echo(f"Run {info('xpert status')} to verify everything is working.", err=True)


# ---------------------------------------------------------------------------
# logs
# ---------------------------------------------------------------------------

@main.command()
@click.option("--container", "-c", type=click.Choice(["nitter", "redis", "all"]), default="all", help="Which container to show logs from")
@click.option("--lines", "-n", default=50, help="Number of lines to show")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
def logs(container: str, lines: int, follow: bool):
    """Tail Nitter and/or Redis container logs."""
    if not MODULES_OK:
        click.echo(err(f"Module error: {MODULE_ERROR}"), err=True)
        sys.exit(1)

    engine_dir = ENGINE_DIR if isinstance(ENGINE_DIR, Path) else Path(ENGINE_DIR)
    if not engine_dir.exists():
        click.echo(err(f"Engine directory not found: {engine_dir}"))
        click.echo("Run 'xpert install' first.")
        sys.exit(1)

    services = []
    if container in ("nitter", "all"):
        services.append("nitter")
    if container in ("redis", "all"):
        services.append("nitter-redis")

    for svc in services:
        click.echo(hdr(f"=== {svc} logs (last {lines} lines) ==="), err=True)
        try:
            cmd = ["docker", "compose", "logs", "--tail", str(lines)]
            if follow:
                cmd.append("-f")
            cmd.append(svc)
            result = subprocess.run(
                cmd,
                cwd=str(engine_dir),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.stdout:
                click.echo(dim(result.stdout))
            if result.stderr:
                click.echo(err(result.stderr))
        except subprocess.TimeoutExpired:
            click.echo(err("Logs command timed out."))
        except Exception as e:
            click.echo(err(f"Error fetching logs: {e}"))


# ---------------------------------------------------------------------------
# Media Download
# ---------------------------------------------------------------------------

@main.command()
@click.argument("source", required=False)
@click.option("--tweet-url", help="Tweet URL to download media from")
@click.option("--user", help="Username to download profile media")
@click.option("--output", "-o", default=".", help="Output directory (default: current directory)")
@click.option("--limit", "-n", type=int, default=None, help="Max images to download per tweet")
@click.option("--include-banner", is_flag=True, default=True, help="Include banner for profile downloads")
def download(source: str, tweet_url: Optional[str], user: Optional[str], output: str, limit: Optional[int], include_banner: bool):
    """Download media assets from tweets or user profiles.

    Examples:
        xpert download --tweet-url "https://x.com/user/status/123"
        xpert download --user elonmusk --output ./media
        xpert download https://x.com/user/status/123
    """
    if not MODULES_OK:
        click.echo(err("Module error: %s" % MODULE_ERROR), err=True)
        sys.exit(1)

    from xpert.media import download_tweet_media, download_profile_media

    # Resolve source
    url_to_fetch = None
    if tweet_url:
        url_to_fetch = tweet_url
    elif source and ("/status/" in source or "x.com" in source or "twitter.com" in source or "nitter" in source):
        url_to_fetch = source

    downloaded_paths = []

    if url_to_fetch:
        ensure_nitter_running()
        click.echo(info("Fetching tweet..."), err=True)
        try:
            tweet = get_tweet(url_to_fetch)
            click.echo("Downloading media from @%s..." % tweet.author, err=True)
            paths = download_tweet_media(tweet, output_dir=output, limit=limit)
            downloaded_paths.extend(paths)
        except Exception as e:
            handle_error(e, "download")
    elif user:
        ensure_nitter_running()
        user = user.lstrip("@")
        click.echo(info("Fetching profile for @%s..." % user), err=True)
        try:
            paths = download_profile_media(user, output_dir=output, include_banner=include_banner)
            downloaded_paths.extend(paths)
        except Exception as e:
            handle_error(e, "download")
    else:
        click.echo(err("Provide either --tweet-url or --user"), err=True)
        click.echo(download.get_help(ctx=None))
        sys.exit(1)

    if downloaded_paths:
        click.echo(ok("\nDownloaded %d file(s) to %s:" % (len(downloaded_paths), Path(output).resolve())))
        for p in downloaded_paths:
            click.echo("  %s" % dim(str(p)))
    else:
        click.echo(warn("No media found to download."))


# ---------------------------------------------------------------------------
# Account Management
# ---------------------------------------------------------------------------

@main.group(invoke_without_command=True)
@click.pass_context
def account(ctx):
    """Manage multi-account proxy configurations (sessions)."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

@account.command("add")
@click.argument("alias")
@click.option("--auth-token", required=True, help="auth_token cookie")
@click.option("--ct0", required=True, help="ct0 cookie")
def account_add(alias, auth_token, ct0):
    """Add a new Twitter account session."""
    try:
        cookies_module.save_cookies(auth_token, ct0, username=alias, account_id=alias)
        click.echo(ok(f"Account '{alias}' added successfully!"))
    except Exception as e:
        click.echo(err(f"Failed to add account: {e}"), err=True)

@account.command("list")
def account_list():
    """List loaded Twitter accounts."""
    try:
        accounts = cookies_module.get_all_accounts()
        if not accounts:
            click.echo(warn("No accounts found in sessions.jsonl."))
            return
        click.echo(hdr("Loaded Accounts:"), err=True)
        for acc in accounts:
            id_str = acc.get('id') or acc.get('username') or 'unnamed'
            click.echo(f"- {ok(id_str)} (auth: {acc.get('auth_token_prefix')}...)", err=True)
    except Exception as e:
        click.echo(err(f"Failed to list accounts: {e}"), err=True)

@account.command("remove")
@click.argument("alias")
def account_remove(alias):
    """Remove a Twitter account by alias."""
    try:
        cookies_module.clear_cookies(alias)
        click.echo(ok(f"Account '{alias}' seamlessly decoupled from sessions.jsonl!"))
    except Exception as e:
        click.echo(err(f"Failed to remove account: {e}"), err=True)

