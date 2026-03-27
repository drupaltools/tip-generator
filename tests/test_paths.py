"""Tests for path resolution: DATA_DIR, get_tips_dir, get_env_file_path, etc."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from tip_generator import (
    DATA_DIR,
    PACKAGE_DIR,
    PROJECT_ROOT,
    _find_project_root,
    ensure_data_dir,
    get_config_file_path,
    get_default_generate_dir,
    get_env_file_path,
    get_tips_dir,
)


class TestConstants:
    def test_data_dir_points_to_home(self):
        assert DATA_DIR == Path.home() / ".drupaltools" / "tip-generator"

    def test_package_dir_exists(self):
        assert PACKAGE_DIR.exists()
        assert (PACKAGE_DIR / "__init__.py").exists()


class TestFindProjectRoot:
    def test_finds_pyproject_toml_ancestor(self):
        # We know the repo has pyproject.toml above src/tip_generator/
        result = _find_project_root()
        assert result is not None
        assert (result / "pyproject.toml").exists()

    def test_returns_none_when_no_pyproject(self):
        with patch("tip_generator.PACKAGE_DIR", Path("/tmp/nonexistent/path")):
            assert _find_project_root() is None


class TestGetTipsDir:
    def test_default(self):
        result = get_tips_dir()
        assert result == DATA_DIR / "tips"

    def test_cli_override(self):
        result = get_tips_dir("/custom/tips")
        assert result == Path("/custom/tips").resolve()

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("TIPGEN_TIPS_DIR", "/env/tips")
        result = get_tips_dir()
        assert result == Path("/env/tips").resolve()

    def test_cli_takes_priority_over_env(self, monkeypatch):
        monkeypatch.setenv("TIPGEN_TIPS_DIR", "/env/tips")
        result = get_tips_dir("/cli/tips")
        assert result == Path("/cli/tips").resolve()

    def test_dev_fallback_uses_local_tips(self, sample_tip_dir, monkeypatch):
        # Clear env override
        monkeypatch.delenv("TIPGEN_TIPS_DIR", raising=False)
        # When a local tips/ exists with .md files and pyproject.toml is above,
        # get_tips_dir should use it. We mock PROJECT_ROOT to point to our tmp.
        with patch("tip_generator.PROJECT_ROOT", sample_tip_dir.parent):
            result = get_tips_dir()
            assert result == sample_tip_dir


class TestGetEnvFilePath:
    def test_default(self, monkeypatch):
        # Must patch PROJECT_ROOT to avoid dev fallback to real project
        monkeypatch.delenv("TIPGEN_ENV_FILE", raising=False)
        with patch("tip_generator.PROJECT_ROOT", None):
            result = get_env_file_path()
            assert result == DATA_DIR / ".env"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("TIPGEN_ENV_FILE", "/custom/.env")
        result = get_env_file_path()
        assert result == Path("/custom/.env").resolve()

    def test_dev_fallback(self, sample_env, monkeypatch):
        monkeypatch.delenv("TIPGEN_ENV_FILE", raising=False)
        with patch("tip_generator.PROJECT_ROOT", sample_env.parent):
            result = get_env_file_path()
            assert result == sample_env

    def test_no_dev_fallback_when_no_local_env(self, tmp_path, monkeypatch):
        monkeypatch.delenv("TIPGEN_ENV_FILE", raising=False)
        with patch("tip_generator.PROJECT_ROOT", tmp_path):
            result = get_env_file_path()
            assert result == DATA_DIR / ".env"


class TestGetConfigFilePath:
    def test_default(self, monkeypatch):
        monkeypatch.delenv("TIPGEN_CONFIG_FILE", raising=False)
        with patch("tip_generator.PROJECT_ROOT", None):
            result = get_config_file_path()
            assert result == DATA_DIR / "config.json"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("TIPGEN_CONFIG_FILE", "/custom/config.json")
        result = get_config_file_path()
        assert result == Path("/custom/config.json").resolve()

    def test_dev_fallback(self, sample_config, monkeypatch):
        monkeypatch.delenv("TIPGEN_CONFIG_FILE", raising=False)
        with patch("tip_generator.PROJECT_ROOT", sample_config.parent):
            result = get_config_file_path()
            assert result == sample_config


class TestEnsureDataDir:
    def test_creates_directory_structure(self, tmp_path):
        with patch("tip_generator.DATA_DIR", tmp_path / "data"):
            ensure_data_dir()
            assert (tmp_path / "data" / "tips").is_dir()
            assert (tmp_path / "data" / "cache").is_dir()

    def test_seeds_env_template(self, tmp_path):
        data_dir = tmp_path / "data"
        with patch("tip_generator.DATA_DIR", data_dir):
            ensure_data_dir()
            env_file = data_dir / ".env"
            assert env_file.exists()
            content = env_file.read_text()
            assert "API Keys" in content
            assert "ANTHROPIC_API_KEY" in content

    def test_does_not_overwrite_existing_env(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True)
        (data_dir / ".env").write_text("KEEP=me")
        with patch("tip_generator.DATA_DIR", data_dir):
            ensure_data_dir()
            assert (data_dir / ".env").read_text() == "KEEP=me"

    def test_seeds_config_from_package(self, tmp_path):
        data_dir = tmp_path / "data"
        with patch("tip_generator.DATA_DIR", data_dir):
            ensure_data_dir()
            config_file = data_dir / "config.json"
            assert config_file.exists()
            # Should have categories
            import json
            data = json.loads(config_file.read_text())
            assert "categories" in data

    def test_does_not_overwrite_existing_config(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True)
        (data_dir / "config.json").write_text('{"keep": true}')
        with patch("tip_generator.DATA_DIR", data_dir):
            ensure_data_dir()
            import json
            assert json.loads((data_dir / "config.json").read_text()) == {"keep": True}


class TestGetDefaultGenerateDir:
    def test_returns_data_dir_tips(self):
        result = get_default_generate_dir()
        assert result == DATA_DIR / "tips"
