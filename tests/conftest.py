"""Shared fixtures for tip_generator tests."""

import json
import pytest
from pathlib import Path


@pytest.fixture
def sample_tip_dir(tmp_path):
    """Create a temp tips/ directory with sample .md files in two categories."""
    tips_dir = tmp_path / "tips"
    core_dir = tips_dir / "core-service"
    drush_dir = tips_dir / "rare-drush-command"
    core_dir.mkdir(parents=True)
    drush_dir.mkdir(parents=True)

    (core_dir / "a1b2c3d4.md").write_text(
        "---\ncategory: core-service\ntitle: Typed Data Manager\ngenerated: 2026-01-01T00:00:00\n---\n\n"
        "The TypedDataManager is a core service that creates typed data objects.\n"
    )
    (core_dir / "e5f6g7h8.md").write_text(
        "---\ncategory: core-service\ntitle: Entity Type Manager\ngenerated: 2026-01-02T00:00:00\n---\n\n"
        "Use `\\Drupal::entityTypeManager()` to load entity type handlers.\n"
    )
    (drush_dir / "9i0j1k2l.md").write_text(
        "---\ncategory: rare-drush-command\ntitle: Drush php-eval shortcut\ngenerated: 2026-01-03T00:00:00\n---\n\n"
        "Run `drush ev '\\Drupal::logger()->notice(\"hello\")'` to execute PHP.\n"
    )

    return tips_dir


@pytest.fixture
def sample_config(tmp_path):
    """Create a minimal config.json with 3 categories."""
    config = {
        "prompt_template": "Generate a Drupal tip for category #{cat_id}: {cat_desc}",
        "code_language": "php",
        "categories": {
            "1": {"name": "proposed-new-module", "desc": "Proposed new module"},
            "35": {"name": "core-service", "desc": "Lesser-known core service"},
            "8": {"name": "rare-drush-command", "desc": "Rare or underused Drush command"},
        },
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))
    return config_path


@pytest.fixture
def sample_env(tmp_path):
    """Create a minimal .env file with test API keys."""
    env_path = tmp_path / ".env"
    env_path.write_text(
        "# Test API keys\n"
        "TIPGEN_OPENAI_API_KEY=sk-test-openai\n"
        "TIPGEN_ANTHROPIC_API_KEY=sk-test-anthropic\n"
    )
    return env_path
