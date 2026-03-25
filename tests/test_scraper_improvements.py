"""Tests for newly improved scraper features using mocked HTML."""

import pytest
from bs4 import BeautifulSoup
from xpert.scraper import _parse_tweet

def test_parse_tweet_with_community_note():
    """Verify that community notes are correctly extracted."""
    html = """
    <div class="tweet-body">
        <span class="username">@user</span>
        <div class="tweet-content"><p>Misleading information</p></div>
        <a class="tweet-date" href="/user/status/123"></a>
        <div class="community-note">
            <div class="community-note-body">
                Actually, here is the context that was missing.
            </div>
        </div>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    body = soup.select_one(".tweet-body")
    result = _parse_tweet(body)
    
    assert result["has_community_note"] is True
    assert "Actually, here is the context" in result["community_note"]

def test_parse_tweet_with_edited_status():
    """Verify that the edited flag is correctly set via .tweet-published a[href*='/history']."""
    html = """
    <div class="tweet-body">
        <span class="username">@user</span>
        <div class="tweet-content"><p>Fixed typo</p></div>
        <a class="tweet-date" href="/user/status/123"></a>
        <p class="tweet-published">
            <a href="/user/status/123/history">Last edited Mar 25, 2026</a>
        </p>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    body = soup.select_one(".tweet-body")
    result = _parse_tweet(body)

    assert result["is_edited"] is True

def test_parse_tweet_with_image_alt_text():
    """Verify that images are returned as List[dict] with alt text."""
    html = """
    <div class="tweet-body">
        <span class="username">@user</span>
        <div class="tweet-content"><p>Look at this</p></div>
        <a class="tweet-date" href="/user/status/123"></a>
        <div class="attachments">
            <div class="attachment image">
                <a class="still-image" href="/pic/orig/img1.jpg">
                    <img src="/pic/img1.jpg" alt="A beautiful sunset">
                </a>
            </div>
            <div class="attachment image">
                <a class="still-image" href="/pic/orig/img2.jpg">
                    <img src="/pic/img2.jpg" alt="A cute cat">
                </a>
            </div>
        </div>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    body = soup.select_one(".tweet-body")
    result = _parse_tweet(body)
    
    assert len(result["images"]) == 2
    assert result["images"][0]["url"].endswith("img1.jpg")
    assert result["images"][0]["alt"] == "A beautiful sunset"
    assert result["images"][1]["alt"] == "A cute cat"

def test_parse_tweet_without_improvements():
    """Verify defaults for tweets without new features."""
    html = """
    <div class="tweet-body">
        <span class="username">@user</span>
        <div class="tweet-content"><p>Just a normal tweet</p></div>
        <a class="tweet-date" href="/user/status/123"></a>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    body = soup.select_one(".tweet-body")
    result = _parse_tweet(body)
    
    assert result["has_community_note"] is False
    assert result["community_note"] == ""
    assert result["is_edited"] is False
    assert result["is_ai_generated"] is False
    assert result["is_promoted"] is False
    assert result["grok_share"] == ""
    assert result["images"] == []


def test_parse_tweet_with_grok_share():
    """Verify that grok_share is extracted from .card .card-destination 'Answer by Grok'."""
    html = """
    <div class="tweet-body">
        <span class="username">@user</span>
        <div class="tweet-content"><p>An interesting question</p></div>
        <a class="tweet-date" href="/user/status/123"></a>
        <div class="card large">
            <div class="card-destination">Answer by Grok</div>
            <h2 class="card-title">Why is the sky blue?</h2>
            <p class="card-description">The sky appears blue due to Rayleigh scattering of sunlight.</p>
        </div>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    body = soup.select_one(".tweet-body")
    result = _parse_tweet(body)

    assert result["grok_share"] == "Why is the sky blue?"


def test_parse_tweet_with_ai_attribution():
    """Verify that is_ai_generated is True when a .attribution link is present."""
    html = """
    <div class="tweet-body">
        <span class="username">@user</span>
        <div class="tweet-content"><p>An AI-generated insight</p></div>
        <a class="tweet-date" href="/user/status/123"></a>
        <a class="attribution" href="/grok">Analyzed by Grok</a>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    body = soup.select_one(".tweet-body")
    result = _parse_tweet(body)

    assert result["is_ai_generated"] is True
    assert result["grok_share"] == ""  # No card with "Answer by Grok"
