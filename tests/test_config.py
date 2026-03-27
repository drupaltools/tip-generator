"""Tests for config loading, env loading, and related functions."""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from tip_generator import load_config, load_env_file, reload_config


class TestLoadConfig:
    def test_reads_categories(self, sample_config):
        with patch("tip_generator.CONFIG_FILE", sample_config):
            config = load_config()
            assert "categories" in config
            assert len(config["categories"]) == 3
            assert "35" in config["categories"]

    def test_raises_for_missing_file(self, tmp_path):
        missing = tmp_path / "nonexistent.json"
        with patch("tip_generator.CONFIG_FILE", missing):
            with pytest.raises(FileNotFoundError, match="Config file not found"):
                load_config()


class TestLoadEnvFile:
    def test_loads_key_value_pairs(self, sample_env, monkeypatch):
        monkeypatch.delenv("TIPGEN_OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("TIPGEN_ANTHROPIC_API_KEY", raising=False)
        with patch("tip_generator.ENV_FILE", sample_env):
            load_env_file()
        assert os.environ.get("TIPGEN_OPENAI_API_KEY") == "sk-test-openai"
        assert os.environ.get("TIPGEN_ANTHROPIC_API_KEY") == "sk-test-anthropic"

    def test_skips_comments(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("# This is a comment\nKEY=value\n")
        monkeypatch.delenv("KEY", raising=False)
        with patch("tip_generator.ENV_FILE", env_file):
            load_env_file()
        assert os.environ.get("KEY") == "value"

    def test_skips_blank_lines(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("\n\nKEY=value\n\n")
        monkeypatch.delenv("KEY", raising=False)
        with patch("tip_generator.ENV_FILE", env_file):
            load_env_file()
        assert os.environ.get("KEY") == "value"

    def test_skips_lines_without_equals(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("no equals sign here\nKEY=value\n")
        with patch("tip_generator.ENV_FILE", env_file):
            load_env_file()
        assert os.environ.get("KEY") == "value"


class TestReloadConfig:
    def test_updates_categories(self, sample_config, monkeypatch):
        with patch("tip_generator.get_config_file_path", return_value=sample_config):
            import tip_generator
            old_count = len(tip_generator.CATEGORIES)
            reload_config()
            assert len(tip_generator.CATEGORIES) == 3
            assert 35 in tip_generator.CATEGORIES
