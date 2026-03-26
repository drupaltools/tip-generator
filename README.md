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

**Using Anthropic:**
```bash
.venv/bin/python tip_generator.py -c 35 -n 5 -p anthropic
```

**Using OpenAI (batch mode - 50% cheaper):**
```bash
.venv/bin/python tip_generator.py -c 35 -n 5 -p openai
```

**Using OpenRouter:**
```bash
.venv/bin/python tip_generator.py -c 35 -n 5 -p openrouter
```

### Arguments

| Argument | Description |
|----------|-------------|
| `-c, --category` | Category number(s) or `all` |
| `-n, --count` | Number of tips per category (default: 5) |
| `-p, --provider` | LLM provider: `anthropic`, `openai`, `openrouter` |
| `-m, --model` | Override default model |
| `-u, --api-url` | Custom API URL for OpenAI/Anthropic-compatible endpoints |
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
.venv/bin/python tip_generator.py -c 35 -n 3 -p openrouter

# Generate 5 tips for multiple categories
.venv/bin/python tip_generator.py -c 35,36,37 -n 5 -p openrouter

# Generate 1 tip for ALL categories
.venv/bin/python tip_generator.py -c all -n 1 -p openrouter

# Use a specific model
.venv/bin/python tip_generator.py -c 35 -n 5 -p openrouter -m anthropic/claude-opus-4

# Use a custom API URL (e.g., local LLM server)
.venv/bin/python tip_generator.py -c 35 -n 5 -p openai -u http://localhost:11434/v1
```

## Batch API Notes

| Provider | Batch Support | Discount | Notes |
|----------|---------------|----------|-------|
| Anthropic | Yes | 50% | Uses `message-batches-2024-09-24` beta |
| OpenAI | Yes | 50% | Results within 24h |
| OpenRouter | ⚠️ Sync only | - | Batch API not supported |

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
    "1": {"name": "proposed-new-module", "desc": "Proposed new module"},
    "35": {"name": "core-service", "desc": "Lesser-known core service"}
  }
}
```

To add or modify categories, edit `config.json` directly - no code changes needed.

## Development

### Running Tests

```bash
# Dry run to verify configuration
.venv/bin/python tip_generator.py -c 35 -n 1 -p openrouter --dry-run
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

## Web Viewer

A simple web UI to browse tips:

```bash
pip install flask
python tip_viewer.py                    # http://localhost:5000
python tip_viewer.py --port 8080        # Custom port
python tip_viewer.py --host 0.0.0.0     # Public access
python tip_viewer.py --debug            # Debug mode
```

Features:
- Filter tips by category
- Get random tip with one click
- View all tips or browse by category
