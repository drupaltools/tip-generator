"""Tests for pure functions: URL hashing, extraction, markdown cleaning, etc."""

import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from tip_generator import generate_file_id, get_default_api_url, get_default_model, get_env, get_relative_path
from tip_generator.url_cache import clean_markdown, extract_urls, get_url_hash, is_cache_valid, is_homepage_url


class TestGetUrlHash:
    def test_returns_12_char_hex(self):
        result = get_url_hash("https://example.com/page")
        assert len(result) == 12
        assert all(c in "0123456789abcdef" for c in result)

    def test_consistent_for_same_url(self):
        url = "https://drupal.org/node/123"
        assert get_url_hash(url) == get_url_hash(url)

    def test_different_for_different_urls(self):
        assert get_url_hash("https://a.com") != get_url_hash("https://b.com")


class TestExtractUrls:
    def test_extracts_http_urls(self):
        text = "Check https://example.com and http://test.org/page?q=1"
        urls = extract_urls(text)
        assert "https://example.com" in urls
        assert "http://test.org/page?q=1" in urls

    def test_deduplicates(self):
        text = "Go to https://example.com and https://example.com again"
        assert len(extract_urls(text)) == 1

    def test_ignores_plain_text(self):
        assert extract_urls("No URLs here") == []


class TestIsHomepageUrl:
    def test_root_path(self):
        assert is_homepage_url("https://example.com") is True

    def test_root_with_slash(self):
        assert is_homepage_url("https://example.com/") is True

    def test_subpage(self):
        assert is_homepage_url("https://example.com/page") is False

    def test_nested_path(self):
        assert is_homepage_url("https://example.com/docs/api") is False


class TestCleanMarkdown:
    def test_removes_backslash_escapes(self):
        result = clean_markdown("Use \\- dashes and \\*stars\\*")
        assert "\\-" not in result
        assert "\\*" not in result

    def test_collapses_blank_lines(self):
        result = clean_markdown("Line 1\n\n\n\n\nLine 2")
        assert result.count("\n\n") <= 1

    def test_removes_horizontal_rules(self):
        result = clean_markdown("Before\n---\nAfter")
        assert "---" not in result


class TestIsCacheValid:
    def test_recent_entry_is_valid(self):
        entry = {"cached_at": datetime.now().isoformat()}
        assert is_cache_valid(entry) is True

    def test_old_entry_is_invalid(self):
        old_time = (datetime.now() - timedelta(hours=48)).isoformat()
        entry = {"cached_at": old_time}
        assert is_cache_valid(entry) is False

    def test_missing_timestamp_is_invalid(self):
        assert is_cache_valid({}) is False
        assert is_cache_valid({"cached_at": ""}) is False

    def test_custom_max_age(self):
        recent = {"cached_at": datetime.now().isoformat()}
        assert is_cache_valid(recent, max_age_hours=0) is False


class TestGenerateFileId:
    def test_returns_8_char_hex(self):
        result = generate_file_id()
        assert len(result) == 8
        assert all(c in "0123456789abcdef" for c in result)

    def test_unique(self):
        assert generate_file_id() != generate_file_id()


class TestGetRelativePath:
    def test_child_path(self):
        base = Path("/home/user/project")
        child = Path("/home/user/project/src/file.py")
        assert get_relative_path(child, base) == Path("src/file.py")

    def test_same_path(self):
        p = Path("/home/user/project")
        assert get_relative_path(p, p) == Path(".")

    def test_outside_base_returns_original(self):
        base = Path("/home/user/other")
        child = Path("/home/user/project/src/file.py")
        assert get_relative_path(child, base) == child


class TestGetDefaultModel:
    def test_anthropic(self):
        assert isinstance(get_default_model("anthropic"), str)

    def test_openai(self):
        assert isinstance(get_default_model("openai"), str)

    def test_openrouter(self):
        assert isinstance(get_default_model("openrouter"), str)

    def test_unknown(self):
        assert get_default_model("unknown") == "unknown"


class TestGetDefaultApiUrl:
    def test_openrouter_has_default(self):
        assert get_default_api_url("openrouter") == "https://openrouter.ai/api/v1"

    def test_others_default_none(self):
        assert get_default_api_url("anthropic") is None
        assert get_default_api_url("openai") is None


class TestGetEnv:
    def test_checks_tipgen_prefix_first(self, monkeypatch):
        monkeypatch.setenv("TIPGEN_FOO", "tipgen-value")
        monkeypatch.setenv("FOO", "raw-value")
        assert get_env("FOO") == "tipgen-value"

    def test_falls_back_to_raw_env(self, monkeypatch):
        monkeypatch.setenv("FOO", "raw-value")
        assert get_env("FOO") == "raw-value"

    def test_returns_default(self, monkeypatch):
        monkeypatch.delenv("TIPGEN_FOO", raising=False)
        monkeypatch.delenv("FOO", raising=False)
        assert get_env("FOO", "default") == "default"

    def test_returns_none_when_missing(self, monkeypatch):
        monkeypatch.delenv("TIPGEN_FOO", raising=False)
        monkeypatch.delenv("FOO", raising=False)
        assert get_env("FOO") is None
