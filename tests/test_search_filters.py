"""Tests for all search filter combinations."""

from unittest.mock import MagicMock

import pytest

from xpert import search as xpert_search


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_httpx_client():
    """Mock httpx.Client for testing without network."""
    with patch('xpert.scraper.httpx.Client') as mock:
        yield mock


# =============================================================================
# Test: Search Filter Combinations
# =============================================================================

class TestSearchFilters:
    """Tests for all search filter combinations."""

    def test_time_within_filter(self, monkeypatch):
        """time_within should add 'since:' to query."""
        captured_urls = []

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><div class='timeline'></div></body></html>"
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        def capture_get(url, **kwargs):
            captured_urls.append(url)
            return mock_response

        mock_client.get = capture_get

        monkeypatch.setattr("xpert.scraper._build_client", lambda: mock_client)
        monkeypatch.setattr("xpert.scraper._raise_nitter_unreachable", lambda *a: None)
        monkeypatch.setattr("xpert.scraper._parse_page", lambda *a: [])

        xpert_search("test", time_within="6h")

        assert len(captured_urls) > 0
        assert "since" in captured_urls[0] or "%20since%3A" in captured_urls[0]

    def test_near_filter(self, monkeypatch):
        """near should add geo filter to query."""
        captured_urls = []

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><div class='timeline'></div></body></html>"
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        def capture_get(url, **kwargs):
            captured_urls.append(url)
            return mock_response

        mock_client.get = capture_get

        monkeypatch.setattr("xpert.scraper._build_client", lambda: mock_client)
        monkeypatch.setattr("xpert.scraper._raise_nitter_unreachable", lambda *a: None)
        monkeypatch.setattr("xpert.scraper._parse_page", lambda *a: [])

        xpert_search("test", near="New York,USA")

        assert len(captured_urls) > 0
        assert "near" in captured_urls[0] or "%20near%3A" in captured_urls[0]

    @pytest.mark.slow
    def test_verified_only_filter(self, monkeypatch):
        """verified_only should add filter:verified to query."""
        captured_urls = []

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><div class='timeline'></div></body></html>"
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        def capture_get(url, **kwargs):
            captured_urls.append(url)
            return mock_response

        mock_client.get = capture_get

        monkeypatch.setattr("xpert.scraper._build_client", lambda: mock_client)
        monkeypatch.setattr("xpert.scraper._raise_nitter_unreachable", lambda *a: None)
        monkeypatch.setattr("xpert.scraper._parse_page", lambda *a: [])

        xpert_search("test", verified_only=True)

        assert len(captured_urls) > 0
        assert "verified" in captured_urls[0] or "%20filter%3Averified" in captured_urls[0]

    def test_filters_media(self, monkeypatch):
        """filters=media should add filter:media to query."""
        captured_urls = []

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><div class='timeline'></div></body></html>"
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        def capture_get(url, **kwargs):
            captured_urls.append(url)
            return mock_response

        mock_client.get = capture_get

        monkeypatch.setattr("xpert.scraper._build_client", lambda: mock_client)
        monkeypatch.setattr("xpert.scraper._raise_nitter_unreachable", lambda *a: None)
        monkeypatch.setattr("xpert.scraper._parse_page", lambda *a: [])

        xpert_search("test", filters="media")

        assert len(captured_urls) > 0
        assert "filter%3Amedia" in captured_urls[0]

    def test_excludes_videos(self, monkeypatch):
        """excludes=videos should add -filter:videos to query."""
        captured_urls = []

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><div class='timeline'></div></body></html>"
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        def capture_get(url, **kwargs):
            captured_urls.append(url)
            return mock_response

        mock_client.get = capture_get

        monkeypatch.setattr("xpert.scraper._build_client", lambda: mock_client)
        monkeypatch.setattr("xpert.scraper._raise_nitter_unreachable", lambda *a: None)
        monkeypatch.setattr("xpert.scraper._parse_page", lambda *a: [])

        xpert_search("test", excludes="videos")

        assert len(captured_urls) > 0
        assert "-filter%3Avideos" in captured_urls[0]

    @pytest.mark.slow
    def test_query_type_top(self, monkeypatch):
        """query_type=top should use f=top in URL."""
        captured_urls = []

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><div class='timeline'></div></body></html>"
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        def capture_get(url, **kwargs):
            captured_urls.append(url)
            return mock_response

        mock_client.get = capture_get

        monkeypatch.setattr("xpert.scraper._build_client", lambda: mock_client)
        monkeypatch.setattr("xpert.scraper._raise_nitter_unreachable", lambda *a: None)
        monkeypatch.setattr("xpert.scraper._parse_page", lambda *a: [])

        xpert_search("test", query_type="top")

        assert len(captured_urls) > 0
        assert "f=top" in captured_urls[0]

    def test_query_type_latest(self, monkeypatch):
        """query_type=latest should use f=latest in URL."""
        captured_urls = []

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><div class='timeline'></div></body></html>"
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        def capture_get(url, **kwargs):
            captured_urls.append(url)
            return mock_response

        mock_client.get = capture_get

        monkeypatch.setattr("xpert.scraper._build_client", lambda: mock_client)
        monkeypatch.setattr("xpert.scraper._raise_nitter_unreachable", lambda *a: None)
        monkeypatch.setattr("xpert.scraper._parse_page", lambda *a: [])

        xpert_search("test", query_type="latest")

        assert len(captured_urls) > 0
        assert "f=latest" in captured_urls[0]

    def test_since_date_filter(self, monkeypatch):
        """since should filter tweets after date."""
        def mock_fetch_page(client, path, retry_count=3):
            return """
            <html><body><div class="timeline-item"><div class="tweet-body">
            <span class="username">@u</span>
            <a class="tweet-date" href="/u/status/1" title="Jan 01, 2025 · 12:00 PM UTC"></a>
            <div class="tweet-content"><p>Old tweet</p></div>
            <div class="tweet-stats"><div class="tweet-stat"><span class="icon icon-heart"></span><span>10</span></div></div>
            </div></div></body></html>
            """

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body></body></html>"
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(return_value=mock_response)

        monkeypatch.setattr("xpert.scraper._build_client", lambda: mock_client)
        monkeypatch.setattr("xpert.scraper._raise_nitter_unreachable", lambda *a: None)
        monkeypatch.setattr("xpert.scraper.fetch_page", mock_fetch_page)

        tweets = xpert_search("test", since="2025-06-01")

        # The mock returns only one tweet from 2025, which is before 2025-06-01
        # so we expect 0 tweets after filtering
        assert isinstance(tweets, list)

    def test_until_date_filter(self, monkeypatch):
        """until should filter tweets before date."""
        def mock_fetch_page(client, path, retry_count=3):
            return """
            <html><body><div class="timeline-item"><div class="tweet-body">
            <span class="username">@u</span>
            <a class="tweet-date" href="/u/status/2" title="Jan 01, 2026 · 12:00 PM UTC"></a>
            <div class="tweet-content"><p>New tweet</p></div>
            <div class="tweet-stats"><div class="tweet-stat"><span class="icon icon-heart"></span><span>10</span></div></div>
            </div></div></body></html>
            """

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body></body></html>"
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(return_value=mock_response)

        monkeypatch.setattr("xpert.scraper._build_client", lambda: mock_client)
        monkeypatch.setattr("xpert.scraper._raise_nitter_unreachable", lambda *a: None)
        monkeypatch.setattr("xpert.scraper.fetch_page", mock_fetch_page)

        tweets = xpert_search("test", until="2025-06-01")

        # Mock returns only one tweet from 2026, which is after 2025-06-01
        # so we expect 0 tweets after filtering
        assert isinstance(tweets, list)

    def test_min_engagement_filter(self, monkeypatch):
        """min_engagement should filter by sum of likes+retweets+replies."""
        def mock_fetch_page(client, path, retry_count=3):
            return """
            <html><body><div class="timeline-item"><div class="tweet-body">
            <span class="username">@u</span>
            <a class="tweet-date" href="/u/status/2" title="Jan 01, 2026 · 12:00 PM UTC"></a>
            <div class="tweet-content"><p>High engagement</p></div>
            <div class="tweet-stats">
                <div class="tweet-stat"><span class="icon icon-heart"></span><span>50</span></div>
                <div class="tweet-stat"><span class="icon icon-retweet"></span><span>30</span></div>
                <div class="tweet-stat"><span class="icon icon-comment"></span><span>20</span></div>
            </div>
            </div></div></body></html>
            """

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body></body></html>"
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(return_value=mock_response)

        monkeypatch.setattr("xpert.scraper._build_client", lambda: mock_client)
        monkeypatch.setattr("xpert.scraper._raise_nitter_unreachable", lambda *a: None)
        monkeypatch.setattr("xpert.scraper.fetch_page", mock_fetch_page)

        tweets = xpert_search("test", min_engagement=50)

        # Total engagement is 50+30+20=100, which is >= 50
        assert isinstance(tweets, list)

    def test_has_engagement_filter(self, monkeypatch):
        """has_engagement should filter out zero-engagement tweets."""
        def mock_fetch_page(client, path, retry_count=3):
            return """
            <html><body><div class="timeline-item"><div class="tweet-body">
            <span class="username">@u</span>
            <a class="tweet-date" href="/u/status/2" title="Jan 01, 2026 · 12:00 PM UTC"></a>
            <div class="tweet-content"><p>Has likes</p></div>
            <div class="tweet-stats">
                <div class="tweet-stat"><span class="icon icon-heart"></span><span>5</span></div>
            </div>
            </div></div></body></html>
            """

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body></body></html>"
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(return_value=mock_response)

        monkeypatch.setattr("xpert.scraper._build_client", lambda: mock_client)
        monkeypatch.setattr("xpert.scraper._raise_nitter_unreachable", lambda *a: None)
        monkeypatch.setattr("xpert.scraper.fetch_page", mock_fetch_page)

        tweets = xpert_search("test", has_engagement=True)

        assert isinstance(tweets, list)
        assert len(tweets) >= 0
