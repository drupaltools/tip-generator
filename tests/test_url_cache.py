"""Tests for URL cache: caching, retrieval, validation."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from tip_generator.url_cache import (
    cache_content,
    extract_urls,
    get_cached_content,
    get_url_hash,
    is_cache_valid,
)


@pytest.fixture
def cache_dir(tmp_path):
    """Create a temp cache directory."""
    d = tmp_path / "cache"
    d.mkdir()
    with patch("tip_generator.url_cache.CACHE_DIR", d):
        yield d


class TestExtractUrls:
    def test_deduplicates(self):
        text = "See https://a.com and https://a.com again"
        urls = extract_urls(text)
        assert len(urls) == 1

    def test_no_urls(self):
        assert extract_urls("Plain text only") == []

    def test_multiple_different(self):
        text = "https://a.com https://b.org/path http://c.net"
        urls = extract_urls(text)
        assert len(urls) == 3


class TestCacheContent:
    def test_caches_markdown_content(self, cache_dir):
        data = {
            "url": "https://example.com",
            "cached_at": datetime.now().isoformat(),
            "type": "markdown",
            "title": "Example",
            "content": "# Hello\n\nWorld",
        }
        result = cache_content("https://example.com", data)
        assert result.exists()
        assert result.suffix == ".md"

    def test_caches_json_content(self, cache_dir):
        data = {
            "url": "https://api.example.com/data",
            "cached_at": datetime.now().isoformat(),
            "type": "json",
            "content": {"key": "value"},
        }
        result = cache_content("https://api.example.com/data", data)
        assert result.exists()
        assert result.suffix == ".json"


class TestGetCachedContent:
    def test_retrieves_markdown(self, cache_dir):
        data = {
            "url": "https://example.com",
            "cached_at": datetime.now().isoformat(),
            "type": "markdown",
            "title": "Example",
            "content": "# Hello\n\nWorld",
        }
        cache_content("https://example.com", data)
        result = get_cached_content("https://example.com")
        assert result is not None
        assert result["type"] == "markdown"
        assert result["content"] == "# Hello\n\nWorld"
        assert result["title"] == "Example"

    def test_retrieves_json(self, cache_dir):
        data = {
            "url": "https://api.example.com/data",
            "cached_at": datetime.now().isoformat(),
            "type": "json",
            "content": {"key": "value"},
        }
        cache_content("https://api.example.com/data", data)
        result = get_cached_content("https://api.example.com/data")
        assert result is not None
        assert result["type"] == "json"
        assert result["data"] == {"key": "value"}

    def test_returns_none_for_missing(self, cache_dir):
        assert get_cached_content("https://nonexistent.com") is None


class TestIsCacheValid:
    def test_recent_is_valid(self):
        entry = {"cached_at": datetime.now().isoformat()}
        assert is_cache_valid(entry) is True

    def test_old_is_invalid(self):
        entry = {"cached_at": (datetime.now() - timedelta(hours=48)).isoformat()}
        assert is_cache_valid(entry) is False
