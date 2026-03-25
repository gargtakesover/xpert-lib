"""
Export module for Xpert.
Supports CSV, Excel, JSON, and Markdown formats.
"""

import csv
import io
import json
import os
from typing import List, Optional, Union


TWEET_COLUMNS = [
    "id", "url", "author", "author_display", "text",
    "created_at", "likes", "retweets", "replies", "views",
    "content_type", "is_reply", "is_retweet", "is_pinned",
    "is_thread", "thread_position", "thread_length",
]


def _flatten_tweet(tweet) -> dict:
    """Flatten a Tweet object into a dict for CSV/Excel."""
    return {
        "id": tweet.id,
        "url": tweet.url,
        "author": tweet.author,
        "author_display": tweet.author_display,
        "text": tweet.text,
        "created_at": tweet.created_at,
        "likes": tweet.likes,
        "retweets": tweet.retweets,
        "replies": tweet.replies,
        "views": tweet.views,
        "content_type": tweet.content_type,
        "is_reply": tweet.is_reply,
        "is_retweet": tweet.is_retweet,
        "is_pinned": tweet.is_pinned,
        "is_thread": tweet.is_thread,
        "thread_position": tweet.thread_position,
        "thread_length": tweet.thread_length,
    }


def _flatten_user(user) -> dict:
    """Flatten a User object."""
    return {
        "username": user.username,
        "display_name": user.display_name,
        "bio": user.bio,
        "followers": user.followers,
        "following": user.following,
        "tweets": user.tweets,
        "url": user.url,
        "profile_picture": user.profile_picture,
        "joined": user.joined,
        "verified": user.verified,
    }


def tweets_to_csv(tweets: List, output: Optional[str] = None) -> str:
    """Export tweets to CSV."""
    rows = [_flatten_tweet(t) for t in tweets]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=TWEET_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    content = buf.getvalue()
    if output:
        with open(output, "w", newline="", encoding="utf-8") as f:
            f.write(content)
        return output
    return content


def tweets_to_json(tweets: List, output: Optional[str] = None, pretty: bool = True) -> str:
    """Export tweets to JSON."""
    data = [_flatten_tweet(t) for t in tweets]
    indent = 2 if pretty else None
    content = json.dumps(data, indent=indent, ensure_ascii=False)
    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(content)
        return output
    return content


def tweets_to_markdown(tweets: List, output: Optional[str] = None) -> str:
    """Export tweets to Markdown table."""
    lines = ["# Xpert Scrape Results\n"]
    lines.append("| # | Author | Text | Likes | Retweets | Date |")
    lines.append("|---|--------|------|-------|----------|------|")
    for i, t in enumerate(tweets, 1):
        text = t.text[:50] + "..." if len(t.text) > 50 else t.text
        text = text.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {i} | @{t.author} | {text} | {t.likes} | {t.retweets} | {t.created_at[:10]} |")
    content = "\n".join(lines)
    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(content)
        return output
    return content


def tweets_to_excel(tweets: List, output: Optional[str] = None) -> Union[bytes, str]:
    """Export tweets to Excel (.xlsx)."""
    try:
        import pandas as pd  # type: ignore
    except ImportError:
        raise ImportError("pandas and openpyxl required for Excel export. Install with: pip install xpert[excel]")

    rows = [_flatten_tweet(t) for t in tweets]
    df = pd.DataFrame(rows, columns=TWEET_COLUMNS)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Tweets")
        ws = writer.sheets["Tweets"]
        from openpyxl.styles import Font, PatternFill  # type: ignore
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="1DA1F2", end_color="1DA1F2", fill_type="solid")
        for col_idx in range(1, len(TWEET_COLUMNS) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions

    data = buf.getvalue()
    if output:
        with open(output, "wb") as f:
            f.write(data)
        return output
    return data


def tweets_to_format(tweets: List, fmt: str, output: str) -> Union[bytes, str]:
    """Export tweets in specified format. Writes to output file."""
    fmt = fmt.lower()
    if fmt == "csv":
        return tweets_to_csv(tweets, output)
    elif fmt == "excel":
        return tweets_to_excel(tweets, output)
    elif fmt == "markdown":
        return tweets_to_markdown(tweets, output)
    elif fmt == "json":
        return tweets_to_json(tweets, output)
    else:
        raise ValueError(f"Unknown format: {fmt}. Use: csv, excel, json, markdown")
