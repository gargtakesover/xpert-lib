"""
CSS selector registry and health monitoring for xpert scraper.
Tracks all BeautifulSoup selectors so selector rot is detectable.
"""

from bs4 import BeautifulSoup
from typing import Dict, List


SELECTORS: Dict[str, str] = {
    # Tweet content
    "tweet_content": ".tweet-content",
    "tweet_date": ".tweet-date a",
    "username": ".username",
    "fullname": ".fullname",
    "avatar": ".avatar",
    "tweet_stat": ".tweet-stat",
    "still_image": "a.still-image",
    "video": "video, video source",
    "media_gif": ".media-gif img",
    "retweet_header": ".retweet-header",
    "pinned": ".pinned, .icon-pin",
    "replying_to": ".replying-to a, .tweet-reply .username",
    "quote": ".quote",
    "card": ".card",
    "community_note": ".community-note",
    "tweet_published": ".tweet-published",
    "attribution": ".attribution",
    # Profile
    "profile_fullname": ".profile-card-fullname",
    "profile_username": ".profile-card-username",
    "profile_bio": ".profile-bio",
    "profile_location": ".profile-location",
    "profile_website": ".profile-website a",
    "profile_avatar": ".profile-card-avatar",
    "profile_banner": ".profile-banner",
    "profile_stat_num": ".profile-stat-num",
    "profile_stat_header": ".profile-stat-header",
    "verified_icon": ".verified-icon",
    "profile_joindate": ".profile-joindate",
    # Page structure
    "main_tweet": ".main-tweet .tweet-body",
    "main_thread": ".main-thread",
    "timeline_item": ".timeline-item",
    "show_more": ".show-more a",
    "after_tweet": ".after-tweet .tweet-body, .replies .tweet-body",
}


def check_selector_health(html: str) -> Dict[str, int]:
    """
    Check which selectors find elements in given HTML.
    Returns dict of selector_name -> found_count (-1 = selector syntax error).
    """
    soup = BeautifulSoup(html, "lxml")
    results = {}
    for name, selector in SELECTORS.items():
        try:
            els = soup.select(selector)
            results[name] = len(els)
        except Exception:
            results[name] = -1
    return results


def get_degraded_selectors(health: Dict[str, int]) -> List[str]:
    """Return list of selectors that found 0 elements (degraded)."""
    return [name for name, count in health.items() if count == 0]


# Critical selectors — if these degrade, data loss is severe
CRITICAL_SELECTORS = frozenset({
    "tweet_content", "username", "fullname", "timeline_item",
    "profile_fullname", "profile_username",
})
