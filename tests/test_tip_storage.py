"""Tests for tip storage: save_tip, get_all_tip_files, get_random_tip, etc."""

import os
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from tip_generator import (
    DATA_DIR,
    get_all_tip_files,
    get_default_generate_dir,
    get_random_tip,
    print_random_tip,
    save_tip,
)


class TestSaveTip:
    def test_creates_file_with_frontmatter(self, tmp_path):
        cat_info = {"name": "core-service", "desc": "Core services"}
        content = "---\ntitle: My Tip\n---\n\nTip content here."
        result = save_tip(cat_info, content, tips_dir=tmp_path)
        assert result is not None
        assert result.exists()
        text = result.read_text()
        assert "category: core-service" in text
        assert "title: My Tip" in text
        assert "Tip content here." in text

    def test_creates_category_directory(self, tmp_path):
        cat_info = {"name": "brand-new-cat", "desc": "New"}
        save_tip(cat_info, "---\n---\n\nContent.", tips_dir=tmp_path)
        assert (tmp_path / "brand-new-cat").is_dir()

    def test_returns_none_for_empty_content(self, tmp_path):
        cat_info = {"name": "test", "desc": "Test"}
        assert save_tip(cat_info, None, tips_dir=tmp_path) is None
        assert save_tip(cat_info, "", tips_dir=tmp_path) is None

    def test_extracts_title_from_generated_frontmatter(self, tmp_path):
        cat_info = {"name": "test", "desc": "Test"}
        content = "---\ntitle: Extracted Title\n---\n\nBody."
        result = save_tip(cat_info, content, tips_dir=tmp_path)
        text = result.read_text()
        assert "title: Extracted Title" in text
        # Only one title line (not duplicated)
        assert text.count("title:") == 1

    def test_uses_default_dir_when_no_tips_dir(self, tmp_path):
        cat_info = {"name": "test", "desc": "Test"}
        with patch("tip_generator.get_default_generate_dir", return_value=tmp_path):
            result = save_tip(cat_info, "---\n---\n\nContent.")
        assert result is not None
        assert result.parent.name == "test"


class TestGetAllTipFiles:
    def test_finds_all_md_files(self, sample_tip_dir, monkeypatch):
        monkeypatch.delenv("TIPGEN_TIPS_DIR", raising=False)
        with patch("tip_generator.TIPS_DIR", sample_tip_dir):
            files = get_all_tip_files()
            assert len(files) == 3
            assert all(f.suffix == ".md" for f in files)

    def test_returns_empty_for_nonexistent_dir(self, tmp_path):
        with patch("tip_generator.TIPS_DIR", tmp_path / "nope"):
            assert get_all_tip_files() == []


class TestGetRandomTip:
    def test_returns_a_path(self, sample_tip_dir, monkeypatch):
        monkeypatch.delenv("TIPGEN_TIPS_DIR", raising=False)
        with patch("tip_generator.TIPS_DIR", sample_tip_dir):
            result = get_random_tip()
            assert result is not None
            assert isinstance(result, Path)
            assert result.exists()

    def test_returns_none_for_empty_dir(self, tmp_path, monkeypatch):
        monkeypatch.delenv("TIPGEN_TIPS_DIR", raising=False)
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with patch("tip_generator.TIPS_DIR", empty_dir):
            assert get_random_tip() is None


class TestPrintRandomTip:
    def test_prints_tip_content(self, sample_tip_dir, monkeypatch, capsys):
        monkeypatch.delenv("TIPGEN_TIPS_DIR", raising=False)
        with patch("tip_generator.TIPS_DIR", sample_tip_dir):
            result = print_random_tip()
            assert result is True
            output = capsys.readouterr().out
            assert len(output) > 0

    def test_returns_false_for_missing_category(self, sample_tip_dir, monkeypatch, capsys):
        monkeypatch.delenv("TIPGEN_TIPS_DIR", raising=False)
        with patch("tip_generator.TIPS_DIR", sample_tip_dir):
            result = print_random_tip("nonexistent-category")
            assert result is False
            output = capsys.readouterr().out
            assert "not found" in output.lower()

    def test_returns_false_for_empty_tips_dir(self, tmp_path, monkeypatch, capsys):
        monkeypatch.delenv("TIPGEN_TIPS_DIR", raising=False)
        with patch("tip_generator.TIPS_DIR", tmp_path / "nope"):
            result = print_random_tip()
            assert result is False
