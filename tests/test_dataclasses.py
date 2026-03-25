"""Tests for dataclasses (Tweet, User) and dict conversion functions."""

from unittest.mock import MagicMock

import pytest

from xpert import Tweet, User
from xpert.scraper import _dict_to_tweet, _dict_to_user


# =============================================================================
# Test: Tweet Dataclass
# =============================================================================

class TestTweetDataclass:
    """Tests for Tweet dataclass."""

    def test_tweet_defaults(self):
        """Tweet should have correct defaults."""
        t = Tweet(
            id="123", text="Hello", author="user",
            created_at="2026-01-01T00:00:00Z", url="https://x.com/user/status/123"
        )
        assert t.likes == 0
        assert t.retweets == 0
        assert t.replies == 0
        assert t.views == 0
        assert t.content_type == "text"
        assert t.is_reply is False
        assert t.is_retweet is False
        assert t.is_pinned is False
        assert t.is_thread is False
        assert t.images == []
        assert t.videos == []

    def test_tweet_with_media(self):
        """Tweet with media should store correctly."""
        t = Tweet(
            id="456", text="Hello with image", author="user",
            created_at="2026-01-01T00:00:00Z", url="https://x.com/user/status/456",
            content_type="image", images=["https://pbs.twimg.com/img.jpg"]
        )
        assert t.content_type == "image"
        assert len(t.images) == 1
        assert t.images[0] == "https://pbs.twimg.com/img.jpg"

    def test_tweet_video(self):
        """Tweet with video should store correctly."""
        t = Tweet(
            id="789", text="Video tweet", author="user",
            created_at="2026-01-01T00:00:00Z", url="https://x.com/user/status/789",
            content_type="video",
            videos=[{"url": "https://video.url", "thumbnail": "https://thumb.url"}]
        )
        assert t.content_type == "video"
        assert len(t.videos) == 1

    def test_tweet_as_thread_part(self):
        """Thread tweet should have correct metadata."""
        t = Tweet(
            id="100", text="Thread reply", author="user",
            created_at="2026-01-01T00:00:00Z", url="https://x.com/user/status/100",
            is_thread=True, thread_position=2, thread_length=5
        )
        assert t.is_thread is True
        assert t.thread_position == 2
        assert t.thread_length == 5


# =============================================================================
# Test: User Dataclass
# =============================================================================

class TestUserDataclass:
    """Tests for User dataclass."""

    def test_user_defaults(self):
        """User should have correct defaults."""
        u = User(
            username="testuser", display_name="Test User", bio="Hello",
            followers=100, following=50, tweets=200, url="https://x.com/testuser"
        )
        assert u.verified is False
        assert u.banner == ""
        assert u.profile_picture == ""
        assert u.joined == ""

    def test_user_verified(self):
        """Verified user should be marked correctly."""
        u = User(
            username="verified", display_name="Verified", bio="",
            followers=1000, following=0, tweets=0, url="https://x.com/verified",
            verified=True
        )
        assert u.verified is True


# =============================================================================
# Test: Dict Conversion
# =============================================================================

class TestDictConversion:
    """Tests for dict-to-dataclass conversion functions."""

    def test_dict_to_tweet(self):
        """Should convert dict to Tweet correctly."""
        d = {
            "id": "123",
            "text": "Test tweet",
            "author": "testuser",
            "author_display": "Test User",
            "created_at": "2026-01-01T12:00:00Z",
            "url": "https://x.com/testuser/status/123",
            "likes": 10,
            "retweets": 5,
            "replies": 2,
            "views": 100,
            "content_type": "text",
            "is_reply": False,
            "is_retweet": False,
            "is_pinned": False,
            "is_thread": False,
            "thread_position": 0,
            "thread_length": 0,
            "reply_to_user": "",
            "retweeted_by": "",
            "images": [],
            "videos": [],
            "gifs": [],
            "quote_tweet": {},
            "link_card": {},
        }
        t = _dict_to_tweet(d)
        assert t.id == "123"
        assert t.text == "Test tweet"
        assert t.author == "testuser"
        assert t.likes == 10
        assert t.retweets == 5

    def test_dict_to_user(self):
        """Should convert dict to User correctly."""
        d = {
            "username": "testuser",
            "display_name": "Test User",
            "bio": "Test bio",
            "profile_picture": "https://example.com/pic.jpg",
            "banner": "https://example.com/banner.jpg",
            "joined": "March 2023",
            "verified": True,
            "stats": {
                "followers": 1000,
                "following": 500,
                "tweets": 2000,
            },
        }
        u = _dict_to_user(d)
        assert u.username == "testuser"
        assert u.display_name == "Test User"
        assert u.followers == 1000
        assert u.following == 500
        assert u.tweets == 2000
        assert u.verified is True


# =============================================================================
# Test: Xpert Client
# =============================================================================

class TestXpertClient:
    """Tests for Xpert client class."""

    def test_xpert_client_init(self):
        """Xpert should initialize cleanly without api_key."""
        from xpert import Xpert

        client = Xpert()
        # api_key parameter was removed (dead code) — no attributes needed
        assert client is not None

    def test_xpert_client_get_user(self, monkeypatch):
        """Xpert.get_user should delegate to get_user."""
        from xpert import Xpert

        monkeypatch.setattr("xpert.scraper._raise_nitter_unreachable", lambda *a: None)

        mock_get_user = MagicMock(return_value=User(
            username="test", display_name="Test",
            bio="", followers=0, following=0, tweets=0, url="https://x.com/test"
        ))
        monkeypatch.setattr("xpert.scraper.get_user", mock_get_user)

        client = Xpert()
        user = client.get_user("test")

        mock_get_user.assert_called_once_with("test")

    def test_xpert_client_search(self, monkeypatch):
        """Xpert.search should delegate to search function."""
        from xpert import Xpert

        monkeypatch.setattr("xpert.scraper._raise_nitter_unreachable", lambda *a: None)

        mock_search = MagicMock(return_value=[])
        monkeypatch.setattr("xpert.scraper.search", mock_search)

        client = Xpert()
        client.search("test", limit=20)

        mock_search.assert_called_once()
        # Verify the limit was passed correctly
        args, kwargs = mock_search.call_args
        assert kwargs.get('limit') == 20 or (len(args) > 1 and args[1] == 20)
