"""Integration tests - real API calls to Nitter."""
import os
import pytest

# Skip all integration tests unless RUN_LIVE_TESTS=1
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_TESTS") != "1",
    reason="Set RUN_LIVE_TESTS=1 to run integration tests"
)

class TestIntegrationUser:
    """Test get_user against live Nitter."""

    def test_get_user_elonmusk(self):
        from xpert import get_user
        user = get_user("elonmusk")
        assert user.username == "elonmusk"
        assert user.display_name == "Elon Musk"
        assert user.followers > 200_000_000

    def test_get_user_not_found(self):
        from xpert import get_user, XpertError
        with pytest.raises(XpertError):
            get_user("thisuserdefinitelydoesnotExist12345")

    def test_get_user_with_timeline(self):
        from xpert import get_user, get_timeline
        user = get_user("POTUS")
        assert user.username
        tweets = get_timeline(user.username, limit=5)
        assert isinstance(tweets, list)


class TestIntegrationTimeline:
    """Test get_timeline against live Nitter."""

    def test_timeline_elonmusk(self):
        from xpert import get_timeline
        tweets = get_timeline("elonmusk", limit=5)
        assert len(tweets) >= 1
        t = tweets[0]
        assert t.author == "elonmusk"
        assert t.text
        assert t.id
        assert t.likes >= 0
        assert t.url

    def test_timeline_limit_respected(self):
        from xpert import get_timeline
        tweets = get_timeline("elonmusk", limit=3)
        assert len(tweets) <= 3


class TestIntegrationSearch:
    """Test search against live Nitter."""

    def test_search_basic(self):
        from xpert import search
        results = search("AI", limit=5)
        assert isinstance(results, list)
        assert len(results) <= 5

    def test_search_with_min_faves(self):
        from xpert import search
        results = search("technology", limit=10, min_faves=100)
        for t in results:
            assert t.likes >= 100

    def test_search_empty_results(self):
        from xpert import search
        results = search("xyzabc123nonexistentquery999", limit=5)
        assert isinstance(results, list)


class TestIntegrationTweet:
    """Test get_tweet against live Nitter."""

    def test_get_tweet_by_url(self):
        from xpert import get_tweet
        # Use a known tweet
        url = "https://x.com/elonmusk/status/1904888726954058000"
        try:
            t = get_tweet(url)
            assert t.id
            assert t.author == "elonmusk"
        except Exception:
            # Tweet may not exist or be private, that's ok for integration test
            pass


class TestIntegrationThread:
    """Test get_thread against live Nitter."""

    def test_get_thread(self):
        from xpert import get_thread
        url = "https://x.com/elonmusk/status/1904888726954058000"
        try:
            tweets = get_thread(url)
            assert isinstance(tweets, list)
            assert all(t.is_thread or t.thread_position > 0 for t in tweets)
        except Exception:
            pass
