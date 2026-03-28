"""
Media downloader for xpert.
Downloads images, videos, and GIFs from scraped tweets or profiles.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Union
from urllib.parse import urlparse

import httpx

from xpert.config import UA

logger = logging.getLogger(__name__)


def _build_media_client() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": UA}, timeout=30, follow_redirects=True)


def download_file(url: str, output_dir: Path, filename: Optional[str] = None) -> Path:
    """Download a single file to output_dir. Returns Path to downloaded file."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not filename:
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")
        filename = path_parts[-1] if path_parts[-1] else "media"
        filename = filename.split("?")[0]
        if not filename or "." not in filename:
            filename = "media"

    dest = output_dir / filename
    with _build_media_client() as client:
        resp = client.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)

    logger.info("Downloaded: %s -> %s", url, dest)
    return dest


def download_tweet_media(tweet_or_dict, output_dir: str = ".", limit: Optional[int] = None) -> List[Path]:
    """
    Download all media from a tweet.

    Args:
        tweet_or_dict: Tweet object or dict with 'images', 'videos', 'gifs' fields
        output_dir: Directory to save media (created if not exists)
        limit: Max number of images to download (None = all)

    Returns:
        List of Path objects for downloaded files
    """
    output_path = Path(output_dir)
    downloaded = []

    # Extract media from dict or object
    if hasattr(tweet_or_dict, "images"):
        images = tweet_or_dict.images
        videos = tweet_or_dict.videos
        gifs = tweet_or_dict.gifs
    else:
        images = tweet_or_dict.get("images", [])
        videos = tweet_or_dict.get("videos", [])
        gifs = tweet_or_dict.get("gifs", [])

    if limit:
        images = images[:limit]

    def _get_ext(url: str, default: str = "jpg") -> str:
        parsed = urlparse(url)
        path = parsed.path.split("?")[0]
        ext = os.path.splitext(path)[1].lstrip(".")
        # Handle Nitter/Twitter specific formats like :orig or .jpg:large
        if ":" in ext:
            ext = ext.split(":")[0]
        return ext[:5] if ext else default

    # Download images
    for i, img in enumerate(images):
        url = img.get("url") if isinstance(img, dict) else img
        if not url:
            continue
        try:
            ext = _get_ext(url, "jpg")
            filename = f"image_{i+1}.{ext}"
            dest = download_file(url, output_path, filename)
            downloaded.append(dest)
        except Exception as e:
            logger.warning("Failed to download image %s: %s", url, e)

    # Download video thumbnails
    for i, vid in enumerate(videos):
        thumb = vid.get("thumbnail") if isinstance(vid, dict) else None
        if not thumb:
            continue
        try:
            ext = _get_ext(thumb, "jpg")
            filename = f"video_{i+1}_thumb.{ext}"
            dest = download_file(thumb, output_path, filename)
            downloaded.append(dest)
        except Exception as e:
            logger.warning("Failed to download video thumbnail %s: %s", thumb, e)

    # Download GIFs
    for i, gif_url in enumerate(gifs):
        if not gif_url:
            continue
        try:
            ext = _get_ext(gif_url, "mp4")
            filename = f"gif_{i+1}.{ext}"
            dest = download_file(gif_url, output_path, filename)
            downloaded.append(dest)
        except Exception as e:
            logger.warning("Failed to download GIF %s: %s", gif_url, e)

    return downloaded


def download_profile_media(username: str, output_dir: str = ".", include_banner: bool = True) -> List[Path]:
    """
    Download profile picture and banner for a user.

    Args:
        username: Twitter username (with or without @)
        output_dir: Directory to save images
        include_banner: Whether to download banner image

    Returns:
        List of Path objects for downloaded files
    """
    from xpert.scraper import get_user

    output_path = Path(output_dir)
    downloaded = []
    username = username.lstrip("@")

    user = get_user(username)

    def _get_ext(url: str, default: str = "jpg") -> str:
        parsed = urlparse(url)
        path = parsed.path.split("?")[0]
        ext = os.path.splitext(path)[1].lstrip(".")
        if ":" in ext:
            ext = ext.split(":")[0]
        return ext[:5] if ext else default

    if user.profile_picture:
        try:
            ext = _get_ext(user.profile_picture, "jpg")
            filename = f"profile_pic.{ext}"
            dest = download_file(user.profile_picture, output_path, filename)
            downloaded.append(dest)
        except Exception as e:
            logger.warning("Failed to download profile pic: %s", e)

    if include_banner and getattr(user, "banner", None):
        try:
            ext = _get_ext(user.banner, "jpg")
            filename = f"banner.{ext}"
            dest = download_file(user.banner, output_path, filename)
            downloaded.append(dest)
        except Exception as e:
            logger.warning("Failed to download banner: %s", e)

    return downloaded
