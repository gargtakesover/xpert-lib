"""
Xpert CLI - Premium command line interface for Twitter/X data access.

Usage:
    xpert user <username>          Get user profile and recent tweets
    xpert tweet <url>              Scrape a single tweet by URL
    xpert search <query>           Search tweets by query
    xpert timeline <username>       Get user timeline
    xpert thread <url>             Unroll a thread by tweet URL
    xpert cookies                  Manage cookies
    xpert configure                Configure cookies interactively
    xpert status                   Check xpert status and connectivity
    xpert setup                    First-time setup wizard
"""

import sys
import json
import os
from typing import Optional

import click

try:
    from xpert import Xpert, Tweet, User, XpertError, RateLimitError, NotFoundError
    from xpert import get_user, get_timeline, search as xpert_search, get_tweet, get_thread
    from xpert import cookies as cookies_module
    from xpert.config import NITTER_INSTANCES
    from xpert.scraper import check_nitter_health
    from xpert.exporters import tweets_to_format, tweets_to_csv, tweets_to_json
    MODULES_OK = True
except ImportError as e:
    Xpert = Tweet = User = None
    XpertError = RateLimitError = NotFoundError = Exception
    get_user = get_timeline = search = get_tweet = get_thread = None
    cookies_module = None
    check_nitter_health = None
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
    """Print friendly error and exit."""
    if isinstance(error, RateLimitError):
        click.echo(err(f"Rate limited: {error}"), err=True)
        click.echo(warn("Please wait a moment and try again."))
    elif isinstance(error, NotFoundError):
        click.echo(err(f"Not found: {error}"), err=True)
    elif isinstance(error, ConnectionError):
        click.echo(err(f"Connection error: {error}"), err=True)
        click.echo(warn("\nTroubleshooting:"), err=True)
        click.echo("  xpert status       # Check connectivity", err=True)
        click.echo("  xpert setup        # First-time setup", err=True)
    elif isinstance(error, XpertError):
        click.echo(err(f"Error: {error}"), err=True)
    else:
        click.echo(err(f"Unexpected error: {error}"), err=True)
    sys.exit(1)


def output_result(data, fmt: str, output: Optional[str]):
    """Output data in requested format."""
    if fmt == "json":
        if isinstance(data, list):
            out = json.dumps([_tweet_to_dict(t) for t in data], indent=2, ensure_ascii=False)
        else:
            out = json.dumps(_user_to_dict(data), indent=2, ensure_ascii=False)
        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(out)
            click.echo(ok(f"Saved to {output}"))
        else:
            click.echo(out)
    else:
        if not output:
            output = click.prompt("Output file path", type=str)
        if isinstance(data, list):
            tweets_to_format(data, fmt, output)
        else:
            # For user profile, write as JSON then convert if needed
            tweets_to_format([], fmt, output)
        click.echo(ok(f"Saved to {output}"))


def _tweet_to_dict(t: Tweet) -> dict:
    return {
        "id": t.id, "url": t.url, "author": t.author,
        "author_display": t.author_display, "text": t.text,
        "created_at": t.created_at, "likes": t.likes, "retweets": t.retweets,
        "replies": t.replies, "views": t.views, "content_type": t.content_type,
        "is_reply": t.is_reply, "is_retweet": t.is_retweet, "is_pinned": t.is_pinned,
        "is_thread": t.is_thread, "thread_position": t.thread_position,
        "thread_length": t.thread_length, "images": t.images,
    }


def _user_to_dict(u: User) -> dict:
    return {
        "username": u.username, "display_name": u.display_name, "bio": u.bio,
        "followers": u.followers, "following": u.following, "tweets": u.tweets,
        "url": u.url, "profile_picture": u.profile_picture, "joined": u.joined,
        "verified": u.verified,
    }


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(version="1.0.0", prog_name="xpert")
def main():
    """Xpert - Access X data without the API."""
    pass


# ---------------------------------------------------------------------------
# configure
# ---------------------------------------------------------------------------

@main.command()
def configure():
    """Configure cookies interactively."""
    if not MODULES_OK:
        click.echo(err(f"Module error: {MODULE_ERROR}"), err=True)
        sys.exit(1)

    click.echo(hdr("Configure Xpert Cookies"))
    click.echo(dim("Get cookies from twitter.com -> DevTools (F12) -> Application -> Cookies\n"))

    click.echo(info("Steps:"))
    click.echo("  1. Open twitter.com in your browser")
    click.echo("  2. Open Developer Tools (F12)")
    click.echo("  3. Go to Application > Cookies > twitter.com")
    click.echo("  4. Find 'auth_token' and 'ct0' values")
    click.echo("  5. Paste them below\n")

    token = click.prompt("Enter auth_token", type=str, hide_input=False)
    ct0 = click.prompt("Enter ct0", type=str, hide_input=False)

    try:
        cookies_module.save_cookies(token, ct0)
        click.echo(f"\n{ok('Cookies saved successfully!')}")

        valid, msg = cookies_module.validate_cookies(token, ct0)
        if valid:
            click.echo(ok(msg))
        else:
            click.echo(warn(f"Warning: {msg}"))
    except cookies_module.CookieError as e:
        click.echo(err(f"Failed: {e}"), err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# cookies
# ---------------------------------------------------------------------------

@main.command()
@click.option("--token", help="auth_token cookie value")
@click.option("--ct0", help="ct0 cookie value")
@click.option("--clear", is_flag=True, help="Clear saved cookies")
def cookies(token: Optional[str], ct0: Optional[str], clear: bool):
    """Manage cookies for authenticated scraping."""
    if not MODULES_OK:
        click.echo(err("Module error"), err=True)
        sys.exit(1)

    if clear:
        cookies_module.clear_cookies()
        click.echo(ok("Cookies cleared."))
        return

    if token and ct0:
        try:
            cookies_module.save_cookies(token, ct0)
            click.echo(ok("Cookies saved!"))
        except cookies_module.CookieError as e:
            click.echo(err(f"Error: {e}"), err=True)
        return

    # Show status
    status = cookies_module.get_cookies_status()
    click.echo(hdr("Cookie Status"))
    if status["configured"]:
        click.echo(f"{ok('●')} Configured")
        click.echo(f"  auth_token: {status['token_prefix']}...")
        click.echo(f"  ct0: {status['ct0_prefix']}...")
    else:
        click.echo(f"{warn('○')} Not configured")
        click.echo(f"\n  Run: {info('xpert configure')}")
        click.echo(f"  Or:  {info('xpert cookies --token TOKEN --ct0 CT0')}")


# ---------------------------------------------------------------------------
# user
# ---------------------------------------------------------------------------

@main.command()
@click.argument("username")
@click.option("--limit", "-n", default=20, help="Number of tweets")
@click.option("--format", "-f", type=click.Choice(["json", "csv", "excel", "markdown"]), default="json", help="Output format")
@click.option("--output", "-o", help="Output file")
def user(username: str, limit: int, format: str, output: Optional[str]):
    """Get user profile and recent tweets."""
    if not MODULES_OK:
        click.echo(err("Module error"), err=True)
        sys.exit(1)

    username = username.lstrip("@")
    click.echo(f"Fetching @{username}...")

    try:
        profile = get_user(username)
        tweets = get_timeline(username, limit=limit)

        click.echo(f"\n{format_user(profile)}\n")

        if tweets:
            click.echo(hdr(f"Recent Tweets ({len(tweets)}):"))
            for t in tweets[:5]:
                click.echo(f"\n---")
                click.echo(format_tweet(t))
            if len(tweets) > 5:
                click.echo(dim(f"\n... and {len(tweets) - 5} more"))

        output_result({"profile": profile, "tweets": tweets}, format, output)

    except Exception as e:
        handle_error(e, f"user @{username}")


# ---------------------------------------------------------------------------
# tweet
# ---------------------------------------------------------------------------

@main.command()
@click.argument("url")
@click.option("--format", "-f", type=click.Choice(["json", "csv", "excel", "markdown"]), default="json")
@click.option("--output", "-o", help="Output file")
def tweet(url: str, format: str, output: Optional[str]):
    """Scrape a single tweet by URL."""
    if not MODULES_OK:
        click.echo(err("Module error"), err=True)
        sys.exit(1)

    click.echo(f"Fetching tweet...")

    try:
        t = get_tweet(url)
        click.echo(f"\n{format_tweet(t)}\n")
        output_result([t], format, output)
    except Exception as e:
        handle_error(e, "tweet URL")


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

@main.command()
@click.argument("query")
@click.option("--limit", "-n", default=20, help="Number of results")
@click.option("--min-faves", type=int, help="Minimum likes filter")
@click.option("--since", help="Filter tweets since (YYYY-MM-DD)")
@click.option("--format", "-f", type=click.Choice(["json", "csv", "excel", "markdown"]), default="json")
@click.option("--output", "-o", help="Output file")
def search(query: str, limit: int, min_faves: Optional[int], since: Optional[str], format: str, output: Optional[str]):
    """Search tweets by query."""
    if not MODULES_OK:
        click.echo(err("Module error"), err=True)
        sys.exit(1)

    click.echo(f'Searching for "{query}"...')

    try:
        tweets = xpert_search(query, limit=limit, min_faves=min_faves, since=since)

        if not tweets:
            click.echo(warn(f"No results for: {query}"))
            if min_faves:
                click.echo(info("Try removing --min-faves filter"))
            return

        click.echo(hdr(f"Found {len(tweets)} tweets:"))
        for i, t in enumerate(tweets[:10], 1):
            click.echo(f"\n{i}. {format_tweet(t)}")
        if len(tweets) > 10:
            click.echo(dim(f"\n... and {len(tweets) - 10} more"))

        output_result(tweets, format, output)

    except Exception as e:
        handle_error(e, f"search '{query}'")


# ---------------------------------------------------------------------------
# timeline
# ---------------------------------------------------------------------------

@main.command()
@click.argument("username")
@click.option("--limit", "-n", default=20, help="Number of tweets")
@click.option("--format", "-f", type=click.Choice(["json", "csv", "excel", "markdown"]), default="json")
@click.option("--output", "-o", help="Output file")
def timeline(username: str, limit: int, format: str, output: Optional[str]):
    """Get user timeline (recent tweets)."""
    if not MODULES_OK:
        click.echo(err("Module error"), err=True)
        sys.exit(1)

    username = username.lstrip("@")
    click.echo(f"Fetching timeline for @{username}...")

    try:
        tweets = get_timeline(username, limit=limit)

        if not tweets:
            click.echo(warn(f"No tweets found for @{username}"))
            return

        click.echo(hdr(f"@{username}'s Timeline ({len(tweets)} tweets):"))
        for i, t in enumerate(tweets[:10], 1):
            click.echo(f"\n{i}. {format_tweet(t)}")
        if len(tweets) > 10:
            click.echo(dim(f"\n... and {len(tweets) - 10} more"))

        output_result(tweets, format, output)

    except Exception as e:
        handle_error(e, f"timeline @{username}")


# ---------------------------------------------------------------------------
# thread
# ---------------------------------------------------------------------------

@main.command()
@click.argument("url")
@click.option("--format", "-f", type=click.Choice(["json", "csv", "excel", "markdown"]), default="json")
@click.option("--output", "-o", help="Output file")
def thread(url: str, format: str, output: Optional[str]):
    """Unroll/expand a thread by tweet URL."""
    if not MODULES_OK:
        click.echo(err("Module error"), err=True)
        sys.exit(1)

    click.echo("Fetching thread...")

    try:
        tweets = get_thread(url)

        if not tweets:
            click.echo(warn("No thread found"))
            return

        click.echo(hdr(f"Thread ({len(tweets)} tweets):"))
        for t in tweets:
            click.echo(f"\n{hdr(f'Tweet {t.thread_position}/{t.thread_length}')}")
            click.echo(format_tweet(t))

        output_result(tweets, format, output)

    except Exception as e:
        handle_error(e, f"thread {url}")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

@main.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed info")
def status(verbose: bool):
    """Check xpert status, cookies, and Nitter connectivity."""
    click.echo(hdr("Xpert Status"))
    click.echo("")

    if not MODULES_OK:
        click.echo(f"{err('✗')} Module error: {MODULE_ERROR}")
        sys.exit(1)

    # Cookies
    click.echo(info("Authentication:"))
    status_cookies = cookies_module.get_cookies_status()
    if status_cookies["configured"]:
        click.echo(f"  {ok('●')} Cookies configured")
        click.echo(f"    auth_token: {status_cookies['token_prefix']}...")
        click.echo(f"    ct0: {status_cookies['ct0_prefix']}...")
    else:
        click.echo(f"  {warn('○')} Cookies not configured")
        click.echo(f"    Run: {info('xpert configure')}")

    click.echo("")

    # Nitter
    click.echo(info("Nitter Connectivity:"))
    for inst in NITTER_INSTANCES[:3]:
        ok_nitter, msg = check_nitter_health(inst)
        if ok_nitter:
            click.echo(f"  {ok('●')} {inst}: {msg}")
        else:
            click.echo(f"  {err('✗')} {inst}: {msg}")
            if verbose:
                click.echo(err("  Troubleshooting:"))
                click.echo("    docker ps | grep nitter", err=True)
                click.echo("    cd ~/takeover/nitter && docker compose up -d", err=True)

    click.echo("")
    if cookies_module.has_cookies() and check_nitter_health(NITTER_INSTANCES[0])[0]:
        click.echo(ok("Xpert is ready! Run 'xpert user <username>' to get started."))
    else:
        click.echo(warn("Xpert needs attention. Run 'xpert setup' for guidance."))


# ---------------------------------------------------------------------------
# setup
# ---------------------------------------------------------------------------

@main.command()
def setup():
    """First-time setup wizard."""
    click.echo(hdr("Welcome to Xpert!"))
    click.echo("")
    click.echo("Let's get you set up to access X data from the command line.\n")

    # Python version
    click.echo(info("1. Python version:"))
    v = sys.version_info
    if v.major >= 3 and v.minor >= 9:
        click.echo(f"  {ok(f'Python {v.major}.{v.minor}.{v.micro} ✓')}")
    else:
        click.echo(f"  {warn(f'Python {v.major}.{v.minor} (recommended: 3.9+)')}")
    click.echo("")

    # Nitter
    click.echo(info("2. Nitter connectivity:"))
    if check_nitter_health:
        ok_n, msg = check_nitter_health(NITTER_INSTANCES[0])
        if ok_n:
            click.echo(f"  {ok('●')} Nitter OK")
        else:
            click.echo(f"  {err('✗')} Nitter unreachable: {msg}")
            click.echo(warn("\n  Start Nitter:"))
            click.echo("    cd ~/takeover/nitter && docker compose up -d")
    click.echo("")

    # Cookies
    click.echo(info("3. Authentication cookies:"))
    if cookies_module and cookies_module.has_cookies():
        click.echo(f"  {ok('●')} Cookies configured")
    else:
        click.echo(f"  {warn('○')} Not configured")
        click.echo(f"\n  Run: {info('xpert configure')}")

    click.echo("")
    click.echo(hdr("Next steps:"))
    click.echo("  xpert configure           # Configure cookies (required)")
    click.echo("  xpert user <username>     # Get a user profile")
    click.echo("  xpert search <query>     # Search tweets")
    click.echo("  xpert status             # Check everything")
    click.echo("")
    click.echo(ok("You're ready to use Xpert!"))
