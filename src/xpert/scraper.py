"""
Xpert - Twitter/X Data Access Library

A reliable library for accessing Twitter/X data via Nitter.
Supports: user profiles, timelines, search, threads, and exports.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Any
from urllib.parse import unquote

import httpx  # type: ignore
from bs4 import BeautifulSoup  # type: ignore

from xpert.config import NITTER_INSTANCES, UA, REQUEST_TIMEOUT, DEFAULT_LIMIT
from xpert.circuit_breaker import nitter_circuit

try:
    from importlib.metadata import version as _get_version
    __version__ = _get_version("xpert")
except Exception:
    __version__ = "1.0.0"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Tweet:
    """Structured tweet data."""
    id: str
    text: str
    author: str
    created_at: str
    url: str
    author_display: str = ""
    author_picture: str = ""
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    views: int = 0
    content_type: str = "text"  # text, image, video, gif, quote, reply, thread_starter
    is_reply: bool = False
    is_retweet: bool = False
    is_pinned: bool = False
    is_thread: bool = False
    thread_position: int = 0
    thread_length: int = 0
    reply_to_user: str = ""
    retweeted_by: str = ""
    images: List[str] = field(default_factory=list)
    videos: List[dict] = field(default_factory=list)
    gifs: List[str] = field(default_factory=list)
    quote_tweet: dict = field(default_factory=dict)
    link_card: dict = field(default_factory=dict)


@dataclass
class User:
    """Structured user profile data."""
    username: str
    display_name: str
    bio: str
    followers: int
    following: int
    tweets: int
    url: str
    profile_picture: str = ""
    banner: str = ""
    joined: str = ""
    verified: bool = False


class XpertError(Exception):
    """Base exception for Xpert errors."""
    pass


class RateLimitError(XpertError):
    """Rate limit exceeded."""
    pass


class NotFoundError(XpertError):
    """Resource not found."""
    pass


# ---------------------------------------------------------------------------
# Cookie-aware HTTP client
# ---------------------------------------------------------------------------

def _build_client() -> httpx.Client:
    """Build HTTP client for Nitter.

    Note: Nitter handles Twitter authentication internally via sessions.jsonl.
    No auth headers needed from Python client.
    """
    headers = {"User-Agent": UA}
    return httpx.Client(headers=headers, timeout=REQUEST_TIMEOUT, follow_redirects=True)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def check_nitter_health(base_url: Optional[str] = None) -> tuple[bool, str]:
    """Check if a Nitter instance is reachable."""
    base_url = base_url or NITTER_INSTANCES[0]
    try:
        r = httpx.get(base_url, headers={"User-Agent": UA}, timeout=5)
        if r.status_code == 200:
            return True, "OK"
        return False, f"HTTP {r.status_code}"
    except httpx.ConnectError:
        return False, "Connection refused"
    except httpx.TimeoutException:
        return False, "Connection timed out (5s timeout)"
    except httpx.NameResolutionError:
        return False, "DNS resolution failed"
    except httpx.HTTPError as e:
        return False, f"HTTP error: {e}"


def _raise_nitter_unreachable(base_url: Optional[str] = None) -> None:
    """Raise ConnectionError with troubleshooting steps if Nitter is down."""
    base_url = base_url or NITTER_INSTANCES[0]
    ok, error_msg = check_nitter_health(base_url)
    if not ok:
        raise ConnectionError(
            f"\n❌ Nitter is not reachable at {base_url}\n"
            f"Error: {error_msg}\n\n"
            f"Troubleshooting:\n"
            f"  - Check if Nitter is running: docker ps | grep nitter\n"
            f"  - Start Nitter: cd ~/takeover/nitter && docker compose up -d\n"
            f"  - Or run: xpert setup\n"
        )


def parse_count(text: str) -> Optional[int]:
    """Parse K/M/B multipliers from engagement counts."""
    if not text:
        return None
    text = text.strip().replace(",", "")
    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    for suffix, mult in multipliers.items():
        if text.upper().endswith(suffix):
            try:
                return int(float(text[:-1]) * mult)
            except ValueError:
                return None
    try:
        return int(text)
    except ValueError:
        return None


def parse_exact_timestamp(date_link) -> Optional[str]:
    """Parse exact ISO timestamp from Nitter's title attribute.

    Nitter provides: title="Mar 14, 2026 · 1:41 PM UTC"
    Returns: "2026-03-14T13:41:00Z"
    """
    if not date_link:
        return None
    title = date_link.get("title", "")
    if not title:
        return None
    title = title.replace(" · ", " ").replace(" UTC", "")
    formats = [
        "%b %d, %Y %I:%M %p",
        "%b %d, %Y %H:%M",
        "%d %b %Y %I:%M %p",
        "%d %b %Y %H:%M",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(title, fmt)
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue
    return None


def nitter_to_twitter_url(nitter_src: str) -> Optional[str]:
    """Convert Nitter proxy URL to Twitter CDN URL."""
    if not nitter_src or "/pic/" not in nitter_src:
        return nitter_src
    path = nitter_src.split("/pic/")[1]
    decoded = unquote(path).split("?")[0]
    res = f"https://pbs.twimg.com/{decoded}"
    return res


def get_download_url(media_url: str) -> str:
    """Get full resolution download URL."""
    if "/media/" in media_url and not media_url.endswith(":orig"):
        return media_url.split("?")[0] + ":orig"
    return media_url


# ---------------------------------------------------------------------------
# Core fetch
# ---------------------------------------------------------------------------

def fetch_page(client: httpx.Client, path: str, retry_count: int = 3) -> Optional[str]:
    """Fetch from Nitter with circuit breaker, rate limiting, and multi-instance fallback."""
    if not nitter_circuit.can_execute():
        return None

    # Wait if we're in rate limit backoff or have too many requests in flight
    from xpert.rate_limiter import rate_limit_and_wait, record_request, record_429, record_success
    rate_limit_and_wait()

    for instance in NITTER_INSTANCES:
        for attempt in range(retry_count):
            try:
                r = client.get(f"{instance}{path}", timeout=REQUEST_TIMEOUT)
                record_request()

                if r.status_code == 429:
                    record_429()
                    nitter_circuit.record_failure()
                    # Don't break — try next instance
                    break

                if r.status_code != 200:
                    nitter_circuit.record_failure()
                    break

                # Check for Nitter-internal rate limit or error page
                if "<title>Error |" in r.text or "error-panel" in r.text:
                    if "rate limit" in r.text.lower() or "429" in r.text:
                        record_429()
                        raise RateLimitError("Nitter is rate limited. Please wait before retrying.")
                    nitter_circuit.record_failure()
                    break

                if any(x in r.text for x in ["tweet-content", "timeline-item", "profile-result"]):
                    nitter_circuit.record_success()
                    record_success()
                    res_text: str = r.text
                    return res_text
                break
            except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadTimeout) as e:
                nitter_circuit.record_failure()
                wait = min(0.5 * (2 ** attempt), 5.0)
                time.sleep(wait)
            except Exception:
                nitter_circuit.record_failure()
                break
    return None


# ---------------------------------------------------------------------------
# Tweet parsing
# ---------------------------------------------------------------------------

def _parse_tweet(body) -> dict[str, Any]:
    """Parse a tweet-body HTML element into a Tweet dataclass."""
    now = datetime.now(timezone.utc).isoformat()

    # Author
    username_el = body.select_one(".username")
    username: str = username_el.get_text(strip=True).lstrip("@") if username_el else ""
    display_el = body.select_one(".fullname")
    display_name = display_el.get_text(strip=True) if display_el else username
    avatar_el = body.select_one(".avatar")
    profile_picture: str = ""
    if avatar_el:
        src = avatar_el.get("src", "")
        if src:
            res_pic = nitter_to_twitter_url(src) if "/pic/" in src else src
            profile_picture = res_pic or ""

    # Content
    content_el = body.select_one(".tweet-content")
    text = content_el.get_text("\n", strip=True) if content_el else ""

    # Timestamp
    date_link = body.select_one(".tweet-date a")
    exact_timestamp: Optional[str] = parse_exact_timestamp(date_link)
    relative_time = date_link.get_text(strip=True) if date_link else None
    tweet_id = ""
    if date_link:
        m = re.search(r"/status/(\d+)", date_link.get("href", ""))
        if m:
            tweet_id = m.group(1)

    # Stats
    replies = retweets = likes = views = 0
    stats = body.select(".tweet-stat")
    for stat in stats:
        icon = None
        for span in stat.select("span[class*='icon-']"):
            classes = span.get("class", [])
            for c in classes:
                if c.startswith("icon-") and c != "icon-container":
                    icon = c
                    break
            if icon:
                break
        if not icon:
            continue
        val = parse_count(stat.get_text(strip=True)) or 0
        if icon == "icon-comment":
            replies = val
        elif icon == "icon-retweet":
            retweets = val
        elif icon == "icon-heart":
            likes = val
        elif icon == "icon-views":
            views = val

    # Media
    images = []
    for a in body.select("a.still-image"):
        img = a.select_one("img")
        if img:
            src = img.get("src", "")
            if src:
                twitter_url = nitter_to_twitter_url(src) if "/pic/" in src else src
                images.append(twitter_url)

    videos = []
    for v in body.select("video, video source"):
        src = v.get("src", v.get("data-url", ""))
        if src:
            if src.startswith("/"):
                src = NITTER_INSTANCES[0] + src
            poster = v.get("poster", None)
            thumb = nitter_to_twitter_url(poster) if poster and "/pic/" in poster else poster
            videos.append({"url": src, "thumbnail": thumb})

    gifs = []
    for g in body.select(".media-gif img"):
        src = g.get("src", "")
        if src:
            gifs.append(nitter_to_twitter_url(src) if "/pic/" in src else src)

    # Type detection
    is_retweet = False
    retweeted_by = ""
    rt_header = body.select_one(".retweet-header")
    if rt_header:
        is_retweet = True
        retweeted_by = rt_header.get_text(strip=True).replace(" retweeted", "").strip()

    is_pinned = body.select_one(".pinned, .icon-pin") is not None

    if videos:
        content_type = "video"
    elif gifs:
        content_type = "gif"
    elif images:
        content_type = "image"
    elif body.select_one(".quote"):
        content_type = "quote"
    else:
        content_type = "text"

    # Reply detection
    reply_to_el = body.select_one(".replying-to a, .tweet-reply .username")
    is_reply = reply_to_el is not None
    reply_to_user = reply_to_el.get_text(strip=True).lstrip("@") if reply_to_el else ""

    # Quote tweet
    quote_tweet = {}
    quote_el = body.select_one(".quote")
    if quote_el:
        q_user = quote_el.select_one(".username")
        q_name = quote_el.select_one(".fullname")
        q_text = quote_el.select_one(".quote-text")
        q_link = quote_el.select_one(".quote-link")
        q_href = q_link.get("href", "") if q_link else ""
        q_id_match = re.search(r"/status/(\d+)", q_href)
        q_username = q_user.get_text(strip=True).lstrip("@") if q_user else ""
        q_images = [
            nitter_to_twitter_url(img.get("src", ""))
            for img in quote_el.select(".quote-media-container img, img")
            if "/pic/" in img.get("src", "")
        ]
        quote_tweet = {
            "id": q_id_match.group(1) if q_id_match else None,
            "url": f"https://x.com/{q_username}/status/{q_id_match.group(1)}" if q_id_match and q_username else None,
            "author": q_username,
            "author_display": q_name.get_text(strip=True) if q_name else q_username,
            "text": q_text.get_text("\n", strip=True) if q_text else "",
            "images": q_images,
        }

    # Link card
    link_card = {}
    card_el = body.select_one(".card")
    if card_el:
        card_title = card_el.select_one(".card-title")
        card_desc = card_el.select_one(".card-description")
        card_dest = card_el.select_one(".card-destination")
        card_link = card_el.select_one("a")
        card_img = card_el.select_one("img")
        card_img_url = None
        if card_img:
            src = card_img.get("src", "")
            if src:
                card_img_url = nitter_to_twitter_url(src) if "/pic/" in src else src
        link_card = {
            "url": card_link.get("href", None) if card_link else None,
            "title": card_title.get_text(strip=True) if card_title else None,
            "description": card_desc.get_text(strip=True) if card_desc else None,
            "destination": card_dest.get_text(strip=True) if card_dest else None,
            "image_url": card_img_url,
        }

    return {
        "id": tweet_id,
        "url": f"https://x.com/{username}/status/{tweet_id}" if username and tweet_id else None,
        "author": username,
        "author_display": display_name,
        "author_picture": profile_picture,
        "text": text,
        "content_type": content_type,
        "created_at": exact_timestamp or now,
        "likes": likes,
        "retweets": retweets,
        "replies": replies,
        "views": views,
        "is_reply": is_reply,
        "reply_to_user": reply_to_user,
        "is_retweet": is_retweet,
        "retweeted_by": retweeted_by,
        "is_pinned": is_pinned,
        "is_thread": False,
        "thread_position": 0,
        "thread_length": 0,
        "images": images,
        "videos": videos,
        "gifs": gifs,
        "quote_tweet": quote_tweet,
        "link_card": link_card,
    }


def _parse_page(html: str) -> List[dict]:
    """Parse all tweets from a page (single tweet, timeline, or search)."""
    soup = BeautifulSoup(html, "lxml")
    tweets = []
    seen_ids = set()

    # Main tweet (single tweet page)
    main_body = soup.select_one(".main-tweet .tweet-body")
    if main_body:
        t = _parse_tweet(main_body)
        if t["id"]:
            seen_ids.add(t["id"])
        tweets.append(t)

    # Thread items
    thread = soup.select_one(".main-thread")
    thread_items = thread.select(".timeline-item") if thread else []
    thread_count = len(thread_items)

    for i, item in enumerate(thread_items):
        body = item.select_one(".tweet-body")
        if body:
            t = _parse_tweet(body)
            if t["id"] and t["id"] in seen_ids:
                continue
            t["is_thread"] = True
            t["thread_position"] = len(seen_ids) + 1
            t["thread_length"] = thread_count + 1
            if t["id"]:
                seen_ids.add(t["id"])
                tweets.append(t)

    # Mark main tweet as thread starter
    if tweets and thread_count >= 1:
        tweets[0]["is_thread"] = True
        tweets[0]["thread_position"] = 1
        tweets[0]["thread_length"] = thread_count + 1
        if tweets[0]["content_type"] == "text":
            tweets[0]["content_type"] = "thread_starter"

    # Replies
    for body in soup.select(".after-tweet .tweet-body, .replies .tweet-body"):
        t = _parse_tweet(body)
        if t["id"] and t["id"] not in seen_ids:
            seen_ids.add(t["id"])
            tweets.append(t)

    # Timeline items (user/search pages)
    if not main_body:
        for item in soup.select(".timeline-item"):
            body = item.select_one(".tweet-body")
            if body:
                t = _parse_tweet(body)
                if t["id"] and t["id"] not in seen_ids:
                    seen_ids.add(t["id"])
                    tweets.append(t)

    return tweets


def _dict_to_tweet(d: dict) -> Tweet:
    """Convert parsed dict to Tweet dataclass."""
    return Tweet(
        id=d.get("id", ""),
        text=d.get("text", ""),
        author=d.get("author", ""),
        author_display=d.get("author_display", ""),
        author_picture=d.get("author_picture", ""),
        created_at=d.get("created_at", ""),
        url=d.get("url", ""),
        likes=d.get("likes", 0),
        retweets=d.get("retweets", 0),
        replies=d.get("replies", 0),
        views=d.get("views", 0),
        content_type=d.get("content_type", "text"),
        is_reply=d.get("is_reply", False),
        is_retweet=d.get("is_retweet", False),
        is_pinned=d.get("is_pinned", False),
        is_thread=d.get("is_thread", False),
        thread_position=d.get("thread_position", 0),
        thread_length=d.get("thread_length", 0),
        reply_to_user=d.get("reply_to_user", ""),
        retweeted_by=d.get("retweeted_by", ""),
        images=d.get("images", []),
        videos=d.get("videos", []),
        gifs=d.get("gifs", []),
        quote_tweet=d.get("quote_tweet", {}),
        link_card=d.get("link_card", {}),
    )


def _dict_to_user(d: dict) -> User:
    """Convert parsed dict to User dataclass."""
    stats = d.get("stats", {})
    return User(
        username=d.get("username", ""),
        display_name=d.get("display_name", ""),
        bio=d.get("bio", "") or "",
        followers=stats.get("followers", 0) or 0,
        following=stats.get("following", 0) or 0,
        tweets=stats.get("tweets", 0) or 0,
        url=f"https://x.com/{d.get('username', '')}",
        profile_picture=d.get("profile_picture", ""),
        banner=d.get("banner", ""),
        joined=d.get("joined", ""),
        verified=d.get("verified", False),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_user(username: str) -> User:
    """Get user profile information."""
    _raise_nitter_unreachable()
    username = username.lstrip("@")
    now = datetime.now(timezone.utc).isoformat()

    with _build_client() as client:
        html = fetch_page(client, f"/{username}")
        if not html:
            raise XpertError(f"Could not fetch profile for @{username}")

    soup = BeautifulSoup(html, "lxml")

    # Display name
    fullname_el = soup.select_one(".profile-card-fullname")
    display_name = fullname_el.get_text(strip=True) if fullname_el else username

    # Actual username
    username_el = soup.select_one(".profile-card-username")
    actual_username = username_el.get_text(strip=True).lstrip("@") if username_el else username

    # Bio
    bio_el = soup.select_one(".profile-bio")
    bio = bio_el.get_text("\n", strip=True) if bio_el else None

    # Profile picture
    profile_picture = ""
    avatar_link = soup.select_one(".profile-card-avatar")
    if avatar_link:
        img = avatar_link.select_one("img")
        if img:
            src = img.get("src", "")
            if src and "/pic/" in src:
                decoded = unquote(src.split("/pic/")[1]).split("?")[0]
                profile_picture = decoded if decoded.startswith("https://") else f"https://pbs.twimg.com/{decoded}"
            elif src:
                profile_picture = src

    # Banner
    banner = ""
    banner_el = soup.select_one(".profile-banner")
    if banner_el:
        img = banner_el.select_one("img")
        if img:
            src = img.get("src", "")
            if src and "/pic/" in src:
                decoded = unquote(src.split("/pic/")[1]).split("?")[0]
                banner = decoded if decoded.startswith("https://") else f"https://pbs.twimg.com/{decoded}"
            elif src:
                banner = src

    # Stats
    stats: dict[str, int] = {"tweets": 0, "following": 0, "followers": 0, "likes": 0}
    stat_els = soup.select(".profile-stat-num")
    stat_headers = soup.select(".profile-stat-header")

    for header, val_el in zip(stat_headers, stat_els):
        label = header.get_text(strip=True).lower()
        val = parse_count(val_el.get_text(strip=True)) or 0
        if label in stats:
            stats[label] = val

    # Verified
    verified = soup.select_one(".verified-icon") is not None

    # Joined
    joined = ""
    join_el = soup.select_one(".profile-joindate")
    if join_el:
        joined_text = join_el.get_text(strip=True)
        m = re.search(r"Joined\s+(\w+\s+\d{4})", joined_text)
        if m:
            joined = m.group(1)
        else:
            joined = joined_text

    return User(
        username=actual_username,
        display_name=display_name,
        bio=bio or "",
        followers=stats["followers"],
        following=stats["following"],
        tweets=stats["tweets"],
        url=f"https://x.com/{actual_username}",
        profile_picture=profile_picture,
        banner=banner,
        joined=joined,
        verified=verified,
    )


def get_timeline(username: str, limit: int = DEFAULT_LIMIT) -> List[Tweet]:
    """Get a user's recent tweets."""
    _raise_nitter_unreachable()
    username = username.lstrip("@")

    all_tweets: List[dict] = []
    seen_ids = set()  # Cross-page dedup
    cursor = ""
    with _build_client() as client:
        while len(all_tweets) < limit:
            path = f"/{username}"
            if cursor:
                path += f"?cursor={cursor}"
            html = fetch_page(client, path)
            if not html:
                break
            parsed = _parse_page(html)
            if not parsed:
                break
            # Cross-page dedup by tweet ID
            for tweet_dict in parsed:
                tweet_id = tweet_dict.get("id", "")
                if tweet_id and tweet_id not in seen_ids:
                    seen_ids.add(tweet_id)
                    all_tweets.append(tweet_dict)
            soup = BeautifulSoup(html, "lxml")
            more = soup.select_one(".show-more a")
            if more and more.get("href"):
                m = re.search(r"cursor=([^&]+)", more["href"])
                cursor = m.group(1) if m else ""
            else:
                break
            time.sleep(0.5)

    return [_dict_to_tweet(t) for t in all_tweets[:limit]]


def search(
    query: str,
    limit: int = DEFAULT_LIMIT,
    min_faves: Optional[int] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    min_retweets: Optional[int] = None,
    min_replies: Optional[int] = None,
    near: Optional[str] = None,
    verified_only: bool = False,
    has_engagement: bool = False,
    min_engagement: Optional[int] = None,
    time_within: Optional[str] = None,
    filters: Optional[str] = None,
    excludes: Optional[str] = None,
    query_type: str = "live",
) -> List[Tweet]:
    """Search tweets by query with full filter support.

    Args:
        query: Search query string
        limit: Maximum results to return
        min_faves: Minimum likes filter
        since: Filter tweets since (YYYY-MM-DD)
        until: Filter tweets until (YYYY-MM-DD)
        min_retweets: Minimum retweets filter
        min_replies: Minimum replies filter
        near: Geo filter (city,country)
        verified_only: Only show verified users
        has_engagement: Exclude zero-engagement tweets
        min_engagement: Minimum in ALL stats (likes+retweets+replies)
        time_within: Relative time (25m, 6h, 7d)
        filters: Include only (media, images, videos, links)
        excludes: Exclude (media, videos)
        query_type: Sort by (live, top, latest)
    """
    _raise_nitter_unreachable()
    from urllib.parse import quote_plus

    # Build query with Nitter-native filters
    full_query = query

    # Add time filter
    if time_within:
        time_map = {"25m": "25m", "6h": "6h", "7d": "7d", "24h": "24h"}
        if time_within in time_map:
            full_query += f" since:{time_map[time_within]}"

    # Add geo filter
    if near:
        full_query += f" near:{near}"

    # Add include filters
    if filters:
        for f in filters.split(","):
            f = f.strip()
            if f == "media":
                full_query += " filter:media"
            elif f == "images":
                full_query += " filter:images"
            elif f == "videos":
                full_query += " filter:videos"
            elif f == "links":
                full_query += " filter:links"

    # Add exclude filters
    if excludes:
        for e in excludes.split(","):
            e = e.strip()
            if e == "media":
                full_query += " -filter:media"
            elif e == "videos":
                full_query += " -filter:videos"

    # Add verified filter
    if verified_only:
        full_query += " filter:verified"

    encoded = quote_plus(full_query)

    # Determine search feed type
    feed_type = "tweets"
    if query_type == "top":
        feed_type = "top"
    elif query_type == "latest":
        feed_type = "latest"
    elif query_type == "people":
        feed_type = "people"

    all_tweets: List[dict] = []
    seen_ids = set()  # Cross-page dedup
    cursor = ""
    with _build_client() as client:
        while len(all_tweets) < limit:
            path = f"/search?f={feed_type}&q={encoded}"
            if cursor:
                path += f"&cursor={cursor}"
            html = fetch_page(client, path)
            if not html:
                break
            parsed = _parse_page(html)
            if not parsed:
                break
            # Cross-page dedup by tweet ID
            for tweet_dict in parsed:
                tweet_id = tweet_dict.get("id", "")
                if tweet_id and tweet_id not in seen_ids:
                    seen_ids.add(tweet_id)
                    all_tweets.append(tweet_dict)
            soup = BeautifulSoup(html, "lxml")
            more = soup.select_one(".show-more a")
            if more and more.get("href"):
                m = re.search(r"cursor=([^&]+)", more["href"])
                cursor = m.group(1) if m else ""
            else:
                break
            time.sleep(0.5)

    tweets = [_dict_to_tweet(t) for t in all_tweets[:limit]]

    # Client-side filtering (for filters Nitter doesn't support natively)
    if min_faves is not None:
        tweets = [t for t in tweets if t.likes >= min_faves]

    if min_retweets is not None:
        tweets = [t for t in tweets if t.retweets >= min_retweets]

    if min_replies is not None:
        tweets = [t for t in tweets if t.replies >= min_replies]

    if since:
        from datetime import datetime
        try:
            since_dt = datetime.fromisoformat(since)
            tweets = [t for t in tweets if t.created_at >= since_dt.isoformat()]
        except ValueError:
            pass

    if until:
        from datetime import datetime
        try:
            until_dt = datetime.fromisoformat(until)
            tweets = [t for t in tweets if t.created_at <= until_dt.isoformat()]
        except ValueError:
            pass

    if has_engagement:
        tweets = [t for t in tweets if t.likes > 0 or t.retweets > 0 or t.replies > 0]

    if min_engagement is not None:
        tweets = [
            t for t in tweets
            if (t.likes or 0) + (t.retweets or 0) + (t.replies or 0) >= min_engagement
        ]

    return tweets


def search_users(query: str, limit: int = DEFAULT_LIMIT) -> List[User]:
    """Search for users by query."""
    _raise_nitter_unreachable()
    from urllib.parse import quote_plus

    encoded = quote_plus(query)
    all_users: List[dict] = []
    cursor = ""
    with _build_client() as client:
        while len(all_users) < limit:
            path = f"/search?f=people&q={encoded}"
            if cursor:
                path += f"&cursor={cursor}"
            html = fetch_page(client, path)
            if not html:
                break

            soup = BeautifulSoup(html, "lxml")
            # Parse user profile cards
            for card in soup.select(".profile-card"):
                user_data = _parse_profile_card(card)
                if user_data:
                    all_users.append(user_data)

            # Check for more results
            more = soup.select_one(".show-more a")
            if more and more.get("href"):
                m = re.search(r"cursor=([^&]+)", more["href"])
                cursor = m.group(1) if m else ""
            else:
                break
            time.sleep(0.5)

    return [_dict_to_user(u) for u in all_users[:limit]]


def _parse_profile_card(card) -> Optional[dict]:
    """Parse a user profile card from search results."""
    username_el = card.select_one(".profile-card-username")
    if not username_el:
        return None
    username = username_el.get_text(strip=True).lstrip("@")

    fullname_el = card.select_one(".profile-card-fullname")
    display_name = fullname_el.get_text(strip=True) if fullname_el else username

    bio_el = card.select_one(".profile-bio")
    bio = bio_el.get_text("\n", strip=True) if bio_el else ""

    # Avatar
    avatar_el = card.select_one(".avatar")
    profile_picture = ""
    if avatar_el:
        src = avatar_el.get("src", "")
        if src:
            res = nitter_to_twitter_url(src) if "/pic/" in src else src
            profile_picture = res or ""

    # Stats
    stats = {"followers": 0, "following": 0, "tweets": 0}
    stat_els = card.select(".profile-stat-num")
    stat_headers = card.select(".profile-stat-header")
    for header, val_el in zip(stat_headers, stat_els):
        label = header.get_text(strip=True).lower()
        val = parse_count(val_el.get_text(strip=True)) or 0
        if label in stats:
            stats[label] = val

    verified = card.select_one(".verified-icon") is not None

    return {
        "username": username,
        "display_name": display_name,
        "bio": bio,
        "stats": stats,
        "profile_picture": profile_picture,
        "banner": "",
        "joined": "",
        "verified": verified,
    }


def get_tweet(url: str) -> Tweet:
    """Scrape a single tweet by URL."""
    _raise_nitter_unreachable()
    match = re.search(r"(?:x\.com|twitter\.com|nitter\.[\w.]+)/(\w+)/status/(\d+)", url)
    if not match:
        raise XpertError(f"Could not parse tweet URL: {url}")

    username, tweet_id = match.groups()
    with _build_client() as client:
        html = fetch_page(client, f"/{username}/status/{tweet_id}")
        if not html:
            raise XpertError(f"Could not fetch tweet from {url}")

    parsed = _parse_page(html)
    if not parsed:
        raise NotFoundError(f"Tweet not found: {url}")

    return _dict_to_tweet(parsed[0])


def get_thread(url: str) -> List[Tweet]:
    """Unroll a full thread from a tweet URL."""
    _raise_nitter_unreachable()
    match = re.search(r"(?:x\.com|twitter\.com|nitter\.[\w.]+)/(\w+)/status/(\d+)", url)
    if not match:
        raise XpertError(f"Could not parse tweet URL: {url}")

    username, tweet_id = match.groups()
    with _build_client() as client:
        html = fetch_page(client, f"/{username}/status/{tweet_id}")
        if not html:
            raise XpertError(f"Could not fetch thread from {url}")

    parsed = _parse_page(html)
    if not parsed:
        raise NotFoundError(f"Thread not found: {url}")

    return [_dict_to_tweet(t) for t in parsed]


# ---------------------------------------------------------------------------
# Xpert Client class
# ---------------------------------------------------------------------------

class Xpert:
    """Main client for accessing Twitter/X data."""

    def get_user(self, username: str) -> User:
        """Get user profile."""
        return get_user(username)

    def get_timeline(self, username: str, limit: int = DEFAULT_LIMIT) -> List[Tweet]:
        """Get user timeline."""
        return get_timeline(username, limit)

    def search(self, query: str, limit: int = DEFAULT_LIMIT) -> List[Tweet]:
        """Search tweets."""
        return search(query, limit)
