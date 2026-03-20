# Drupal Tip Generator

Generate static MD tip files for the `drupal-tip` skill using various LLM providers.

## Setup

### 1. Create Virtual Environment

```bash
cd ~/.claude/skills/drupal-tip
python3 -m venv .venv
source .venv/bin/activate
pip install openai anthropic
```

### 2. Configure API Keys

Copy the example environment file and add your keys:

```bash
cp .env.example .env
```

Edit `.env` with your API keys (use `TIPGEN_` prefix):

```env
TIPGEN_ANTHROPIC_API_KEY=sk-ant-...
TIPGEN_OPENAI_API_KEY=sk-...
TIPGEN_OPENROUTER_API_KEY=sk-or-...
```

## Usage

### Get a Random Existing Tip (FAST!)

Get a tip from the pre-generated database instantly — no API call needed:

```bash
.venv/bin/python tip_generator.py --random-tip
.venv/bin/python tip_generator.py --random-tip --tip-category core-service
.venv/bin/python tip_generator.py --list-existing
```

### List Available Categories

```bash
.venv/bin/python tip_generator.py --list-categories
```

### Generate Tips

**Using Anthropic (sync mode):**
```bash
.venv/bin/python tip_generator.py -c 35 -n 5 -p anthropic --sync
```

**Using OpenAI (batch mode - 50% cheaper):**
```bash
.venv/bin/python tip_generator.py -c 35 -n 5 -p openai
```

**Using OpenRouter (sync mode only):**
```bash
.venv/bin/python tip_generator.py -c 35 -n 5 -p openrouter --sync
```

### Arguments

| Argument | Description |
|----------|-------------|
| `-c, --category` | Category number(s) or `all` |
| `-n, --count` | Number of tips per category (default: 5) |
| `-p, --provider` | LLM provider: `anthropic`, `openai`, `openrouter` |
| `-m, --model` | Override default model |
| `--sync` | Use synchronous API (required for OpenRouter) |
| `--no-wait` | Don't wait for batch completion |
| `--dry-run` | Show what would be done without calling API |
| `--list-categories` | List all available categories |
| `--random-tip` | Get a random existing tip (fast, no API) |
| `--list-existing` | List categories with existing tips |
| `--tip-category` | Filter random tip by category name |
| `--validate` | Enable validation mode |
| `--validate-file` | Validate a specific tip file |
| `--validate-category` | Validate all tips in a category |
| `--validate-all` | Validate all tips across all categories |

### Examples

```bash
# Generate 3 tips for category 35 (core-service)
.venv/bin/python tip_generator.py -c 35 -n 3 -p openrouter --sync

# Generate 5 tips for multiple categories
.venv/bin/python tip_generator.py -c 35,36,37 -n 5 -p openrouter --sync

# Generate 1 tip for ALL categories
.venv/bin/python tip_generator.py -c all -n 1 -p openrouter --sync

# Use a specific model
.venv/bin/python tip_generator.py -c 35 -n 5 -p openrouter -m anthropic/claude-opus-4 --sync
```

## Batch API Notes

| Provider | Batch Support | Discount | Notes |
|----------|---------------|----------|-------|
| Anthropic | ⚠️ Unstable | 50% | Batch API may return 404 - use `--sync` mode |
| OpenAI | Yes | 50% | Results within 24h (uses `max_completion_tokens`) |
| OpenRouter | No | - | Use `--sync` flag |

## Check Batch Status

If you ran batch mode with `--no-wait`:

```bash
.venv/bin/python tip_generator.py --check-batch BATCH_ID -p anthropic
.venv/bin/python tip_generator.py --check-batch BATCH_ID -p openai --save-results
```

## Output

Tips are saved to `tips/{category-name}/{uuid}.md` with 8-character random IDs:

```
tips/
├── core-service/
│   ├── a1b2c3d4.md
│   └── e5f6g7h8.md
└── rare-drush-command/
    └── 9i0j1k2l.md
```

Each file has frontmatter:

```markdown
---
category: core-service
title: [Generated title]
---

[Tip content]
```

## Configuration

Categories and the prompt template are defined in `config.json`:

```json
{
  "prompt_template": "Generate a Drupal tip for category #{cat_id}: {cat_desc}...",
  "code_language": "php",
  "categories": {
    "1": {"name": "proposed-new-module", "live_fetch": true, "desc": "Proposed new module"},
    "35": {"name": "core-service", "live_fetch": false, "desc": "Lesser-known core service"}
  }
}
```

To add or modify categories, edit `config.json` directly - no code changes needed.

## Development

### Running Tests

```bash
# Dry run to verify configuration
.venv/bin/python tip_generator.py -c 35 -n 1 -p openrouter --sync --dry-run
```

## Validation

Validate generated tips for formatting issues, truncation, and quality:

```bash
# Validate a single file
.venv/bin/python tip_generator.py --validate --validate-file tips/core-service/a1b2c3d4.md

# Validate all tips in a category
.venv/bin/python tip_generator.py --validate --validate-category core-service

# Validate ALL tips across all categories
.venv/bin/python tip_generator.py --validate --validate-all
```

### Validation Checks

- **Formatting**: Frontmatter structure, code block balance, line counts
- **Completeness**: Truncation patterns (trailing `...`, `[TODO]`, incomplete code blocks)
- **Quality**: Generic openings, placeholder text, excessive code ratio
- **Fake Content**: Non-existent Drupal APIs, hallucinated functions, wrong service names

## File Structure

```
drupal-tip/
├── .env              # API keys (gitignored)
├── .env.example      # Example configuration
├── .venv/            # Python virtual environment
├── config.json       # Categories and prompt template
├── tip_generator.py  # Main generator script
├── SKILL.md          # Skill definition for Claude Code
├── README.md         # This file
└── tips/             # Generated tip files
    ├── core-service/
    │   ├── a1b2c3d4.md
    │   └── ...
    └── ...
```
