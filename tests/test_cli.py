"""Tests for CLI subcommands via sys.argv manipulation."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from tip_generator import main


def run_cli(*args, tips_dir=None):
    """Helper to run main() with given args, capturing stdout and stderr."""
    from io import StringIO

    buf_out = StringIO()
    buf_err = StringIO()

    original_stdout = sys.stdout
    original_stderr = sys.stderr

    sys.stdout = buf_out
    sys.stderr = buf_err
    sys.argv = ["tip_generator"] + list(args)

    if tips_dir:
        import tip_generator
        tip_generator.TIPS_DIR = tips_dir

    try:
        main()
        return buf_out.getvalue(), buf_err.getvalue(), 0
    except SystemExit as e:
        return buf_out.getvalue(), buf_err.getvalue(), e.code if e.code else 0
    except Exception as e:
        return buf_out.getvalue(), buf_err.getvalue(), 1
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr


class TestListCategories:
    def test_lists_all_categories(self):
        output, err, code = run_cli("--list-categories")
        assert code == 0
        combined = output + err
        assert "90 categories" in combined
        assert "core service" in combined.lower()


class TestListExisting:
    def test_lists_categories_with_tips(self):
        output, err, code = run_cli("--list-existing")
        assert code == 0


class TestRandomTip:
    def test_prints_message_for_empty_dir(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        output, err, code = run_cli("--random-tip", "--tips-dir", str(empty_dir))
        assert code == 0
        combined = output + err
        assert "No tips found" in combined

    def test_prints_tip_from_real_data(self):
        # TIPS_DIR points to real DATA_DIR which has tips
        output, err, code = run_cli("--random-tip")
        assert code == 0
        combined = output + err
        assert len(combined.strip()) > 0


class TestDryRun:
    def test_dry_run_single_category(self):
        output, err, code = run_cli("--dry-run", "-c", "35", "-n", "1", "-p", "openai")
        assert code == 0
        assert "DRY RUN" in output
        assert "35" in output
        assert "openai" in output

    def test_dry_run_all_categories(self):
        output, err, code = run_cli("--dry-run", "-c", "all", "-n", "1", "-p", "anthropic")
        assert code == 0
        assert "DRY RUN" in output
        assert "90" in output

    def test_dry_run_category_slug(self):
        output, err, code = run_cli("--dry-run", "-c", "proposed-new-module", "-n", "1", "-p", "openai")
        assert code == 0
        assert "DRY RUN" in output


class TestErrorCases:
    def test_missing_provider_for_generation(self):
        output, err, code = run_cli("-c", "35")
        combined = output + err
        assert "provider" in combined.lower()

    def test_invalid_category_format(self):
        output, err, code = run_cli("-c", "abc", "-p", "openai")
        combined = output + err
        assert "unknown" in combined.lower()

    def test_validate_without_subflag(self):
        output, err, code = run_cli("--validate")
        combined = output + err
        assert "validate" in combined.lower() and ("file" in combined.lower() or "category" in combined.lower())

    def test_check_batch_requires_provider(self):
        output, err, code = run_cli("--check-batch", "batch-123")
        combined = output + err
        assert "provider" in combined.lower()


class TestValidateFile:
    def test_validates_specific_file(self, sample_tip_dir):
        tip_file = sample_tip_dir / "core-service" / "a1b2c3d4.md"
        output, err, code = run_cli("--validate", "--validate-file", str(tip_file))
        assert code == 0

    def test_nonexistent_file(self, tmp_path):
        output, err, code = run_cli("--validate", "--validate-file", str(tmp_path / "nope.md"))
        assert code == 0
        combined = output + err
        assert "not found" in combined.lower()


class TestValidateCategory:
    def test_validates_category_folder(self, sample_tip_dir):
        output, err, code = run_cli(
            "--validate", "--validate-category", "core-service",
            tips_dir=sample_tip_dir,
        )
        assert code == 0


class TestTipsDirOverride:
    def test_custom_tips_dir(self, tmp_path):
        custom = tmp_path / "custom-tips"
        output, err, code = run_cli("--random-tip", "--tips-dir", str(custom))
        assert code == 0
        combined = output + err
        assert "No tips found" in combined or "tips directory" in combined.lower()
