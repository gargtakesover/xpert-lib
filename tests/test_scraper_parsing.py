"""Tests for scraper parsing functions."""

from unittest.mock import MagicMock, patch

import pytest

from xpert.scraper import (
    parse_count, parse_exact_timestamp, nitter_to_twitter_url,
    check_nitter_health, get_download_url,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_httpx_get():
    """Mock httpx.get for health checks."""
    with patch('xpert.scraper.httpx.get') as mock:
        yield mock


# =============================================================================
# Test: Parse Count
# =============================================================================

class TestParseCount:
    """Tests for parse_count function."""

    def test_k_suffix(self):
        """1.5K should equal 1500."""
        assert parse_count("1.5K") == 1500
        assert parse_count("100K") == 100000

    def test_m_suffix(self):
        """2.3M should equal 2300000."""
        assert parse_count("2.3M") == 2300000
        assert parse_count("1M") == 1000000

    def test_b_suffix(self):
        """1.5B should equal 1500000000."""
        assert parse_count("1.5B") == 1500000000

    def test_plain_number(self):
        """Plain numbers should parse correctly."""
        assert parse_count("100") == 100
        assert parse_count("0") == 0

    def test_empty_string(self):
        """Empty string should return None."""
        assert parse_count("") is None

    def test_non_numeric(self):
        """Non-numeric strings should return None."""
        assert parse_count("abc") is None
        assert parse_count("NaN") is None

    def test_with_commas(self):
        """Numbers with commas should parse correctly."""
        assert parse_count("1,000") == 1000
        assert parse_count("1,500,000") == 1500000


# =============================================================================
# Test: Nitter to Twitter URL
# =============================================================================

class TestNitterToTwitterURL:
    """Tests for nitter_to_twitter_url function."""

    def test_nitter_pic_url(self):
        """Nitter pic URLs should be converted to Twitter CDN URLs."""
        src = "https://nitter.net/pic/profile_images/123.jpg"
        result = nitter_to_twitter_url(src)
        assert result == "https://pbs.twimg.com/profile_images/123.jpg"

    def test_non_pic_url_unchanged(self):
        """Non-pic URLs should be returned unchanged."""
        src = "https://example.com/image.jpg"
        assert nitter_to_twitter_url(src) == src

    def test_empty_url(self):
        """Empty URL should return empty string."""
        assert nitter_to_twitter_url("") == ""

    def test_none_url(self):
        """None URL should return None."""
        assert nitter_to_twitter_url(None) is None


# =============================================================================
# Test: Parse Exact Timestamp
# =============================================================================

class TestParseExactTimestamp:
    """Tests for parse_exact_timestamp function."""

    def test_parses_rfc2822_format(self):
        """Should parse Mar 14, 2026 · 1:41 PM UTC format."""
        class MockEl:
            def get(self, attr, default=None):
                if attr == "title":
                    return "Mar 14, 2026 · 1:41 PM UTC"
                return default

        result = parse_exact_timestamp(MockEl())
        assert result is not None
        assert "2026-03-14" in result

    def test_no_title(self):
        """Element without title should return None."""
        result = parse_exact_timestamp(None)
        assert result is None

    def test_empty_title(self):
        """Element with empty title should return None."""
        class MockEl:
            def get(self, attr, default=None):
                if attr == "title":
                    return ""
                return default

        result = parse_exact_timestamp(MockEl())
        assert result is None


# =============================================================================
# Test: Get Download URL
# =============================================================================

class TestGetDownloadUrl:
    """Tests for get_download_url function."""

    def test_adds_orig_suffix(self):
        """Should add :orig to media URLs."""
        url = "https://nitter.net/media/abc.jpg"
        result = get_download_url(url)
        assert result == "https://nitter.net/media/abc.jpg:orig"

    def test_preserves_existing_orig(self):
        """Should not add :orig if already present."""
        url = "https://nitter.net/media/abc.jpg:orig"
        result = get_download_url(url)
        assert result == url


# =============================================================================
# Test: Check Nitter Health
# =============================================================================

class TestCheckNitterHealth:
    """Tests for check_nitter_health function."""

    def test_health_check_success(self, mock_httpx_get):
        """Successful health check should return True."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx_get.return_value = mock_response

        ok, msg = check_nitter_health("http://localhost:8080")
        assert ok is True
        assert msg == "OK"

    def test_health_check_http_error(self, mock_httpx_get):
        """HTTP error should return False with status code."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_httpx_get.return_value = mock_response

        ok, msg = check_nitter_health("http://localhost:8080")
        assert ok is False
        assert "500" in msg

    def test_health_check_connection_refused(self, mock_httpx_get):
        """Connection refused should return False."""
        import httpx
        mock_httpx_get.side_effect = httpx.ConnectError("Connection refused")

        ok, msg = check_nitter_health("http://localhost:8080")
        assert ok is False
        assert "refused" in msg.lower()

    def test_health_check_timeout(self, mock_httpx_get):
        """Timeout should return False."""
        import httpx
        mock_httpx_get.side_effect = httpx.TimeoutException("timeout")

        ok, msg = check_nitter_health("http://localhost:8080")
        assert ok is False
        assert "timed out" in msg.lower() or "timeout" in msg.lower()
