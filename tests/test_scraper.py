"""Tests for xpert scraper module."""

import pytest
from xpert.scraper import (
    Tweet, User, XpertError,
    parse_count, parse_exact_timestamp, nitter_to_twitter_url,
)


class TestParseCount:
    def test_k_suffix(self):
        assert parse_count("1.5K") == 1500
        assert parse_count("100K") == 100000

    def test_m_suffix(self):
        assert parse_count("2.3M") == 2300000
        assert parse_count("1M") == 1000000

    def test_b_suffix(self):
        assert parse_count("1.5B") == 1500000000

    def test_plain_number(self):
        assert parse_count("100") == 100
        assert parse_count("0") == 0

    def test_empty(self):
        assert parse_count("") is None
        assert parse_count("abc") is None


class TestNitterToTwitterURL:
    def test_nitter_pic_url(self):
        src = "https://nitter.net/pic/profile_images/123.jpg"
        result = nitter_to_twitter_url(src)
        assert result == "https://pbs.twimg.com/profile_images/123.jpg"

    def test_non_pic_url_unchanged(self):
        src = "https://example.com/image.jpg"
        assert nitter_to_twitter_url(src) == src


class TestParseExactTimestamp:
    def test_parses_rfc2822(self):
        # Simulate a date_link with title attribute
        class MockEl:
            def get(self, attr, default=None):
                if attr == "title":
                    return "Mar 14, 2026 · 1:41 PM UTC"
                return default

        result = parse_exact_timestamp(MockEl())
        assert result is not None
        assert "2026-03-14" in result

    def test_no_title(self):
        result = parse_exact_timestamp(None)
        assert result is None


class TestTweetDataclass:
    def test_tweet_defaults(self):
        t = Tweet(
            id="123", text="Hello", author="user",
            created_at="2026-01-01T00:00:00Z", url="https://x.com/user/status/123"
        )
        assert t.likes == 0
        assert t.retweets == 0
        assert t.content_type == "text"
        assert t.is_reply is False
        assert t.images == []

    def test_tweet_with_media(self):
        t = Tweet(
            id="456", text="Hello with image", author="user",
            created_at="2026-01-01T00:00:00Z", url="https://x.com/user/status/456",
            content_type="image", images=["https://pbs.twimg.com/img.jpg"]
        )
        assert t.content_type == "image"
        assert len(t.images) == 1


class TestUserDataclass:
    def test_user_defaults(self):
        u = User(
            username="testuser", display_name="Test User", bio="Hello",
            followers=100, following=50, tweets=200, url="https://x.com/testuser"
        )
        assert u.verified is False
        assert u.banner == ""

    def test_user_verified(self):
        u = User(
            username="verified", display_name="Verified", bio="",
            followers=1000, following=0, tweets=0, url="https://x.com/verified",
            verified=True
        )
        assert u.verified is True
