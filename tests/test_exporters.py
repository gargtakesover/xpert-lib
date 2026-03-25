"""Tests for export functionality."""

import pytest
import json
import tempfile
import os

from xpert.scraper import Tweet
from xpert.exporters import (
    tweets_to_csv, tweets_to_json, tweets_to_markdown,
    tweets_to_excel, tweets_to_format,
)


def make_tweet(**kwargs):
    defaults = dict(
        id="123", text="Hello world", author="testuser",
        created_at="2026-01-01T12:00:00Z", url="https://x.com/testuser/status/123",
        likes=10, retweets=5, replies=2,
    )
    defaults.update(kwargs)
    return Tweet(**defaults)


class TestTweetsToCSV:
    def test_returns_string(self):
        result = tweets_to_csv([make_tweet()])
        assert isinstance(result, str)
        assert "id" in result
        assert "123" in result

    def test_writes_to_file(self, tmp_path):
        out = tmp_path / "tweets.csv"
        result = tweets_to_csv([make_tweet()], str(out))
        assert result == str(out)
        assert out.exists()

    def test_multiple_tweets(self):
        tweets = [
            make_tweet(id="1", text="First"),
            make_tweet(id="2", text="Second"),
        ]
        result = tweets_to_csv(tweets)
        assert "First" in result
        assert "Second" in result


class TestTweetsToJSON:
    def test_returns_string(self):
        result = tweets_to_json([make_tweet()])
        assert isinstance(result, str)
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["id"] == "123"

    def test_pretty_print(self):
        result = tweets_to_json([make_tweet()], pretty=True)
        assert "\n" in result

    def test_compact(self):
        result = tweets_to_json([make_tweet()], pretty=False)
        lines = result.strip().split("\n")
        assert len(lines) <= 2

    def test_empty_list(self):
        result = tweets_to_json([])
        assert result == "[]"


class TestTweetsToMarkdown:
    def test_returns_string(self):
        result = tweets_to_markdown([make_tweet()])
        assert isinstance(result, str)
        assert "|" in result  # Table format

    def test_writes_to_file(self, tmp_path):
        out = tmp_path / "tweets.md"
        result = tweets_to_markdown([make_tweet()], str(out))
        assert result == str(out)
        assert out.exists()


class TestTweetsToFormat:
    def test_csv_dispatcher(self):
        result = tweets_to_format([make_tweet()], "csv", None)
        assert isinstance(result, str)
        assert "123" in result

    def test_json_dispatcher(self):
        result = tweets_to_format([make_tweet()], "json", None)
        assert isinstance(result, str)

    def test_markdown_dispatcher(self):
        result = tweets_to_format([make_tweet()], "markdown", None)
        assert isinstance(result, str)

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError) as exc:
            tweets_to_format([make_tweet()], "invalid", None)
        assert "Unknown format" in str(exc.value)


class TestExcelExport:
    def test_excel_without_pandas(self, monkeypatch):
        monkeypatch.setitem(__import__("sys").modules, "pandas", None)
        with pytest.raises(ImportError):
            tweets_to_excel([make_tweet()])

    def test_excel_with_pandas(self):
        try:
            import pandas
        except ImportError:
            pytest.skip("pandas not available")
        result = tweets_to_excel([make_tweet()])
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_excel_file(self, tmp_path):
        try:
            import pandas
        except ImportError:
            pytest.skip("pandas not available")
        out = tmp_path / "tweets.xlsx"
        result = tweets_to_excel([make_tweet()], str(out))
        assert result == str(out)
        assert out.stat().st_size > 0
