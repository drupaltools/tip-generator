"""Tests for tip parsing and validation."""

from pathlib import Path
from unittest.mock import patch

import pytest

from tip_generator import TipValidator, get_prompt_for_category
from tip_generator.viewer import parse_tip_file


VALID_TIP = """\
---
category: core-service
title: Typed Data Manager
generated: 2026-01-01T00:00:00
---

The TypedDataManager is a core service that creates typed data objects.

```php
$data = \\Drupal::typedDataManager()->create(DataDefinition::create('string'));
```
"""

VALID_TIP_NO_TITLE = """\
---
category: core-service
generated: 2026-01-01T00:00:00
---

Use entity_type.manager service for loading entities.
"""

NO_FRONTMATTER_TIP = """\
This is a tip without frontmatter.

It should still work.
"""


class TestParseTipFile:
    def test_extracts_frontmatter_fields(self, tmp_path):
        tip_file = tmp_path / "core-service" / "a1b2c3d4.md"
        tip_file.parent.mkdir(parents=True)
        tip_file.write_text(VALID_TIP)

        result = parse_tip_file(tip_file)
        assert result["category"] == "core-service"
        assert result["title"] == "Typed Data Manager"
        assert result["generated"] == "2026-01-01T00:00:00"
        assert result["uuid"] == "a1b2c3d4"

    def test_handles_missing_frontmatter(self, tmp_path):
        tip_file = tmp_path / "misc" / "z9y8x7w6.md"
        tip_file.parent.mkdir(parents=True)
        tip_file.write_text(NO_FRONTMATTER_TIP)

        result = parse_tip_file(tip_file)
        assert result["category"] == "misc"
        assert result["title"] == ""

    def test_strips_frontmatter_from_body(self, tmp_path):
        tip_file = tmp_path / "core-service" / "a1b2c3d4.md"
        tip_file.parent.mkdir(parents=True)
        tip_file.write_text(VALID_TIP)

        result = parse_tip_file(tip_file)
        assert "---" not in result["content"]
        assert "TypedDataManager" in result["content"]

    def test_body_has_no_trailing_whitespace(self, tmp_path):
        tip_file = tmp_path / "cat" / "f1.md"
        tip_file.parent.mkdir(parents=True)
        tip_file.write_text(NO_FRONTMATTER_TIP)

        result = parse_tip_file(tip_file)
        assert result["content"] == result["content"].strip()


class TestTipValidator:
    def _write_tip(self, tmp_path, content, filename="tip.md"):
        tip_file = tmp_path / filename
        tip_file.write_text(content)
        return tip_file

    def test_valid_tip_passes(self, tmp_path):
        tip_file = self._write_tip(tmp_path, VALID_TIP)
        validator = TipValidator(tip_file)
        is_valid, errors, warnings = validator.validate()
        assert is_valid is True
        assert errors == []

    def test_empty_file_fails(self, tmp_path):
        tip_file = self._write_tip(tmp_path, "")
        validator = TipValidator(tip_file)
        is_valid, errors, _ = validator.validate()
        assert is_valid is False
        assert any("empty" in e.lower() for e in errors)

    def test_ellipsis_at_end_fails(self, tmp_path):
        content = VALID_TIP_NO_TITLE + "..."
        tip_file = self._write_tip(tmp_path, content)
        validator = TipValidator(tip_file)
        is_valid, errors, _ = validator.validate()
        assert is_valid is False
        assert any("ellipsis" in e.lower() for e in errors)

    def test_unclosed_template_fails(self, tmp_path):
        content = "---\ncategory: test\n---\n\nSome content with {{unfinished"
        tip_file = self._write_tip(tmp_path, content)
        validator = TipValidator(tip_file)
        is_valid, errors, _ = validator.validate()
        assert is_valid is False
        assert any("template" in e.lower() for e in errors)

    def test_generic_opening_warns(self, tmp_path):
        content = "---\ncategory: test\n---\n\nThis is a tip about Drupal that explains things.\n\nMore content here to make it longer and valid enough."
        tip_file = self._write_tip(tmp_path, content)
        validator = TipValidator(tip_file)
        is_valid, errors, warnings = validator.validate()
        assert is_valid is True
        assert any("generic" in w.lower() for w in warnings)

    def test_fake_drupal_api_detected(self, tmp_path):
        content = "---\ncategory: test\n---\n\nUse Drupal::generateUUID() for unique IDs. This is a tip with enough content to pass length checks."
        tip_file = self._write_tip(tmp_path, content)
        validator = TipValidator(tip_file)
        is_valid, errors, _ = validator.validate()
        assert is_valid is False
        assert any("fake" in e.lower() or "non-existent" in e.lower() for e in errors)


class TestGetPromptForCategory:
    def test_includes_category_id_and_desc(self):
        cat_info = {"name": "core-service", "desc": "Lesser-known core service"}
        prompt = get_prompt_for_category(35, cat_info, include_context=False)
        assert "35" in prompt
        assert "Lesser-known core service" in prompt

    def test_does_not_include_cat_name_by_default(self):
        cat_info = {"name": "core-service", "desc": "Lesser-known core service"}
        prompt = get_prompt_for_category(35, cat_info, include_context=False)
        # The default prompt template uses {cat_desc} but not {cat_name}
        assert "core-service" not in prompt

    def test_includes_context_when_url_cache_available(self):
        import tip_generator
        if not tip_generator.HAS_URL_CACHE:
            pytest.skip("url_cache not importable in this environment")
        cat_info = {"name": "test", "desc": "Test category"}
        with patch("tip_generator.build_context_for_category", return_value="Some reference data"):
            prompt = get_prompt_for_category(1, cat_info, include_context=True)
            assert "Some reference data" in prompt
