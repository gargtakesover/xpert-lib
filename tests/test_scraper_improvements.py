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
    """Verify that the edited flag is correctly set."""
    html = """
    <div class="tweet-body">
        <span class="username">@user</span>
        <div class="tweet-content"><p>Fixed typo</p></div>
        <a class="tweet-date" href="/user/status/123"></a>
        <span class="tweet-header-items">
            <span class="icon-pencil" title="Edited"></span>
        </span>
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
                <a href="/pic/orig/img1.jpg">
                    <img src="/pic/img1.jpg" alt="A beautiful sunset">
                </a>
            </div>
            <div class="attachment image">
                <a href="/pic/orig/img2.jpg">
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
    assert result["community_note"] == {}
    assert result["is_edited"] is False
    assert result["images"] == []
