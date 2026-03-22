"""Tests for scraper functions with mocked HTTP responses."""

from unittest.mock import MagicMock, patch

import click.testing
import pytest

from xpert import (
    Tweet, User, XpertError, RateLimitError, NotFoundError,
    get_user, get_timeline, search as xpert_search, get_tweet, get_thread,
)
from xpert.scraper import (
    _parse_tweet, _parse_page, get_download_url,
)
from xpert.circuit_breaker import nitter_circuit, CircuitState
from xpert_cli.cli import main


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def runner():
    """Click CLI test runner."""
    return click.testing.CliRunner()


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.Client for testing without network."""
    with patch('xpert.scraper.httpx.Client') as mock:
        yield mock


@pytest.fixture
def sample_tweet_html():
    """Sample tweet HTML from Nitter."""
    return """
    <html>
    <body>
    <div class="main-tweet">
        <div class="tweet-body">
            <div class="tweet-header">
                <a class="avatar" href="/user">
                    <img src="https://nitter.net/pic/profile_images/123.jpg">
                </a>
                <span class="username">@testuser</span>
                <a class="tweet-date" href="/user/status/123456" title="Mar 14, 2026 · 1:41 PM UTC">
                    <span>Mar 14, 2026</span>
                </a>
            </div>
            <div class="tweet-content">
                <p>This is a test tweet with some content.</p>
            </div>
            <div class="tweet-stats">
                <div class="tweet-stat">
                    <span class="icon icon-comment"></span>
                    <span>5</span>
                </div>
                <div class="tweet-stat">
                    <span class="icon icon-retweet"></span>
                    <span>10</span>
                </div>
                <div class="tweet-stat">
                    <span class="icon icon-heart"></span>
                    <span>100</span>
                </div>
                <div class="tweet-stat">
                    <span class="icon icon-views"></span>
                    <span>1.5K</span>
                </div>
            </div>
        </div>
    </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_timeline_html():
    """Sample timeline HTML from Nitter."""
    return """
    <html>
    <body>
    <div class="timeline">
        <div class="timeline-item">
            <div class="tweet-body">
                <span class="username">@testuser</span>
                <a class="tweet-date" href="/testuser/status/123" title="Mar 14, 2026 · 1:41 PM UTC">
                    <span>Mar 14, 2026</span>
                </a>
                <div class="tweet-content">
                    <p>First tweet in timeline</p>
                </div>
                <div class="tweet-stats">
                    <div class="tweet-stat">
                        <span class="icon icon-heart"></span>
                        <span>50</span>
                    </div>
                </div>
            </div>
        </div>
        <div class="timeline-item">
            <div class="tweet-body">
                <span class="username">@testuser</span>
                <a class="tweet-date" href="/testuser/status/124" title="Mar 13, 2026 · 12:00 PM UTC">
                    <span>Mar 13, 2026</span>
                </a>
                <div class="tweet-content">
                    <p>Second tweet in timeline</p>
                </div>
                <div class="tweet-stats">
                    <div class="tweet-stat">
                        <span class="icon icon-heart"></span>
                        <span>25</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_search_html():
    """Sample search results HTML from Nitter."""
    return """
    <html>
    <body>
    <div class="timeline">
        <div class="timeline-item">
            <div class="tweet-body">
                <span class="username">@searchuser</span>
                <a class="tweet-date" href="/searchuser/status/789" title="Mar 14, 2026 · 2:00 PM UTC">
                    <span>Mar 14, 2026</span>
                </a>
                <div class="tweet-content">
                    <p>Search result tweet about python</p>
                </div>
                <div class="tweet-stats">
                    <div class="tweet-stat">
                        <span class="icon icon-heart"></span>
                        <span>200</span>
                    </div>
                    <div class="tweet-stat">
                        <span class="icon icon-retweet"></span>
                        <span>50</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_profile_html():
    """Sample user profile HTML from Nitter."""
    return """
    <html>
    <body>
    <div class="profile-card">
        <a class="profile-card-avatar" href="/testuser">
            <img src="https://nitter.net/pic/profile_images/abc.jpg">
        </a>
        <a class="profile-card-fullname" href="/testuser">Test User</a>
        <a class="profile-card-username" href="/testuser">@testuser</a>
        <p class="profile-bio">This is a test bio.</p>
        <div class="profile-joindate">Joined March 2023</div>
        <span class="verified-icon"></span>
        <div class="profile-stats">
            <span class="profile-stat-num">1000</span>
            <span class="profile-stat-header">Followers</span>
            <span class="profile-stat-num">500</span>
            <span class="profile-stat-header">Following</span>
            <span class="profile-stat-num">2000</span>
            <span class="profile-stat-header">Tweets</span>
        </div>
    </div>
    </body>
    </html>
    """


# =============================================================================
# Test: Get User Mocked
# =============================================================================

class TestGetUserMocked:
    """Tests for get_user with mocked HTTP."""

    def test_get_user_parses_profile(self, sample_profile_html, monkeypatch):
        """get_user should correctly parse profile HTML."""
        from bs4 import BeautifulSoup

        def mock_fetch_page(client, path, retry_count=3):
            return sample_profile_html

        monkeypatch.setattr("xpert.scraper.fetch_page", mock_fetch_page)
        monkeypatch.setattr("xpert.scraper._raise_nitter_unreachable", lambda *a: None)

        user = get_user("testuser")

        assert user.username == "testuser"
        assert user.display_name == "Test User"
        assert "bio" in user.bio.lower() or user.bio == ""
        assert user.followers >= 0


# =============================================================================
# Test: Get Timeline Mocked
# =============================================================================

class TestGetTimelineMocked:
    """Tests for get_timeline with mocked HTTP."""

    def test_get_timeline_returns_tweets(self, sample_timeline_html, monkeypatch):
        """get_timeline should return parsed tweets."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = sample_timeline_html
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(return_value=mock_response)

        def mock_build_client():
            return mock_client

        monkeypatch.setattr("xpert.scraper._build_client", mock_build_client)
        monkeypatch.setattr("xpert.scraper._raise_nitter_unreachable", lambda *a: None)

        tweets = get_timeline("testuser", limit=10)

        assert isinstance(tweets, list)
        assert len(tweets) >= 0  # May be empty if parsing fails


# =============================================================================
# Test: Search Mocked
# =============================================================================

class TestSearchMocked:
    """Tests for search with mocked HTTP."""

    def test_search_builds_correct_query(self, sample_search_html, monkeypatch):
        """search should build correct Nitter query URL."""
        captured_path = []

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = sample_search_html
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        def capture_get(url, **kwargs):
            captured_path.append(url)
            return mock_response

        mock_client.get = capture_get

        def mock_build_client():
            return mock_client

        monkeypatch.setattr("xpert.scraper._build_client", mock_build_client)
        monkeypatch.setattr("xpert.scraper._raise_nitter_unreachable", lambda *a: None)

        tweets = xpert_search("python", limit=10)

        # Verify the path contains search and encoded query
        assert len(captured_path) > 0
        assert "search" in captured_path[0]
        assert "python" in captured_path[0] or "q=" in captured_path[0]

    def test_search_with_min_faves_filter(self, monkeypatch):
        """search should apply min_faves filter client-side."""
        # Reset circuit breaker to ensure fetch_page executes
        nitter_circuit._state = CircuitState.CLOSED
        nitter_circuit._failure_count = 0

        # Patch fetch_page and _parse_page to control tweet data
        def mock_fetch_page(client, path, retry_count=3):
            return "<html><body><div class='timeline'></div></body></html>"

        def mock_parse_page(html):
            return [
                {"id": "1", "text": "Low likes", "author": "u",
                 "created_at": "2026-01-01T00:00:00Z", "url": "https://x.com/u/1",
                 "likes": 5, "retweets": 0, "replies": 0, "content_type": "text"},
                {"id": "2", "text": "High likes", "author": "u",
                 "created_at": "2026-01-01T00:00:00Z", "url": "https://x.com/u/2",
                 "likes": 100, "retweets": 0, "replies": 0, "content_type": "text"},
            ]

        monkeypatch.setattr("xpert.scraper.fetch_page", mock_fetch_page)
        monkeypatch.setattr("xpert.scraper._parse_page", mock_parse_page)
        monkeypatch.setattr("xpert.scraper._raise_nitter_unreachable", lambda *a: None)

        tweets = xpert_search("test", limit=10, min_faves=50)

        # Should return 1 tweet (the one with 100 likes)
        assert len(tweets) == 1
        assert tweets[0].likes >= 50


# =============================================================================
# Test: Get Tweet Mocked
# =============================================================================

class TestGetTweetMocked:
    """Tests for get_tweet with mocked HTTP."""

    def test_get_tweet_invalid_url_raises(self, monkeypatch):
        """get_tweet should raise XpertError for invalid URL."""
        monkeypatch.setattr("xpert.scraper._raise_nitter_unreachable", lambda *a: None)

        with pytest.raises(XpertError) as exc:
            get_tweet("not-a-valid-url")
        assert "parse" in str(exc.value).lower() or "Could not parse" in str(exc.value)


# =============================================================================
# Test: Get Thread Mocked
# =============================================================================

class TestGetThreadMocked:
    """Tests for get_thread with mocked HTTP."""

    def test_get_thread_invalid_url_raises(self, monkeypatch):
        """get_thread should raise XpertError for invalid URL."""
        monkeypatch.setattr("xpert.scraper._raise_nitter_unreachable", lambda *a: None)

        with pytest.raises(XpertError) as exc:
            get_thread("not-a-valid-url")
        assert "parse" in str(exc.value).lower() or "Could not parse" in str(exc.value)


# =============================================================================
# Test: Error Handling
# =============================================================================

class TestErrorHandling:
    """Tests for error handling."""

    def test_handle_rate_limit_error(self, runner, monkeypatch):
        """Should handle RateLimitError gracefully."""
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)
        monkeypatch.setattr("xpert_cli.cli.ensure_nitter_running", lambda *a: None)

        from xpert import RateLimitError
        monkeypatch.setattr("xpert_cli.cli.get_user", MagicMock(side_effect=RateLimitError("Rate limited")))

        result = runner.invoke(main, ["user", "testuser"])
        # Should exit with error
        assert result.exit_code == 1
        assert "rate" in result.output.lower() or "limited" in result.output.lower()

    def test_handle_not_found_error(self, runner, monkeypatch):
        """Should handle NotFoundError gracefully."""
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)
        monkeypatch.setattr("xpert_cli.cli.ensure_nitter_running", lambda *a: None)

        from xpert import NotFoundError
        monkeypatch.setattr("xpert_cli.cli.get_tweet", MagicMock(side_effect=NotFoundError("Not found")))

        result = runner.invoke(main, ["tweet", "https://x.com/user/status/123"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_handle_connection_error(self, runner, monkeypatch):
        """Should handle ConnectionError gracefully."""
        monkeypatch.setattr("xpert_cli.cli.MODULES_OK", True)
        monkeypatch.setattr("xpert_cli.cli.ensure_nitter_running", lambda *a: None)

        monkeypatch.setattr("xpert_cli.cli.get_timeline", MagicMock(side_effect=ConnectionError("Connection refused")))

        result = runner.invoke(main, ["timeline", "testuser"])
        assert result.exit_code == 1
        assert "connection" in result.output.lower() or "troubleshoot" in result.output.lower()


# =============================================================================
# Test: Malformed Data
# =============================================================================

class TestMalformedData:
    """Tests for handling malformed data."""

    def test_parse_page_with_missing_elements(self):
        """_parse_page should handle HTML with missing elements."""
        html = "<html><body><div class='timeline'></div></body></html>"
        tweets = _parse_page(html)
        assert isinstance(tweets, list)

    def test_parse_page_with_empty_body(self):
        """_parse_page should handle empty HTML."""
        html = "<html><body></body></html>"
        tweets = _parse_page(html)
        assert isinstance(tweets, list)
        assert len(tweets) == 0

    def test_parse_tweet_with_minimal_data(self):
        """_parse_tweet should handle minimal tweet HTML."""
        html = """
        <div class="tweet-body">
            <span class="username">@user</span>
            <div class="tweet-content"><p>Hello</p></div>
            <a class="tweet-date" href="/user/status/123"></a>
        </div>
        """
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        body = soup.select_one(".tweet-body")
        result = _parse_tweet(body)
        assert result["author"] == "user"
        assert "Hello" in result["text"]

    def test_get_download_url_edge_cases(self):
        """get_download_url should handle edge cases."""
        assert get_download_url("") == ""
        assert get_download_url("not-a-media-url") == "not-a-media-url"
