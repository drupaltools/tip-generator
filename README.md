# Drupal Tip Generator

[![PyPI](https://img.shields.io/pypi/v/drupaltools-tip-generator)](https://pypi.org/project/drupaltools-tip-generator/)
[![License: GPL-2.0-or-later](https://img.shields.io/pypi/l/drupaltools-tip-generator)](LICENSE)

Generate static MD tip files for the `drupal-tip` skill using various LLM providers.

## Installation

### Option 1: Install via pip (Recommended)

```bash
pip install drupaltools-tip-generator

# Get a random tip
drupaltools-tip-generator --random-tip

# Generate new tips
drupaltools-tip-generator -c 35 -n 5 -p openai
```

### Option 2: Install via skills CLI

```bash
# Install for OpenCode
npx skills add drupaltools/tip-generator --agent opencode

# Or install via shskills
pip install shskills
shskills install --url https://github.com/drupaltools/tip-generator --agent opencode
```

### Option 3: Clone and run from source

```bash
# Clone the repository
git clone https://github.com/drupaltools/tip-generator.git ~/.claude/skills/drupal-tip
cd ~/.claude/skills/drupal-tip

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Get a random tip
python -m tip_generator --random-tip
```

## Setup (for generating new tips)

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
drupaltools-tip-generator --random-tip
drupaltools-tip-generator --random-tip --tip-category core-service
drupaltools-tip-generator --list-existing
```

### List Available Categories

```bash
drupaltools-tip-generator --list-categories
```

### Generate Tips

**Using Anthropic:**
```bash
drupaltools-tip-generator -c 35 -n 5 -p anthropic
```

**Using OpenAI (batch mode - 50% cheaper):**
```bash
drupaltools-tip-generator -c 35 -n 5 -p openai
```

**Using OpenRouter:**
```bash
drupaltools-tip-generator -c 35 -n 5 -p openrouter
```

### Arguments

| Argument | Description |
|----------|-------------|
| `-c, --category` | Category number(s) or `all` |
| `-n, --count` | Number of tips per category (default: 5) |
| `-p, --provider` | LLM provider: `anthropic`, `openai`, `openrouter` |
| `-m, --model` | Override default model |
| `-u, --api-url` | Custom API URL for OpenAI/Anthropic-compatible endpoints |
| `-t, --max-tokens` | Maximum tokens for response (default: 4096) |
| `--tips-dir` | Custom tips directory (or set `TIPGEN_TIPS_DIR` env var or `tips_dir` in config.json) |
| `--save-truncated` | Save tips even if truncated (use with caution) |
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
drupaltools-tip-generator -c 35 -n 3 -p openrouter

# Generate 5 tips for multiple categories
drupaltools-tip-generator -c 35,36,37 -n 5 -p openrouter

# Generate 1 tip for ALL categories
drupaltools-tip-generator -c all -n 1 -p openrouter

# Use a specific model
drupaltools-tip-generator -c 35 -n 5 -p openrouter -m anthropic/claude-opus-4

# Use a custom API URL (e.g., Together.xyz, local LLM server)
drupaltools-tip-generator -c 35 -n 5 -p openai -u https://api.together.xyz/v1

# Increase max tokens for longer responses (avoid truncation)
drupaltools-tip-generator -c 60 -n 20 -p openai --max-tokens 8192

# Save tips even if truncated (use with caution)
drupaltools-tip-generator -c 35 -n 5 -p openai --save-truncated
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
drupaltools-tip-generator --check-batch BATCH_ID -p anthropic
drupaltools-tip-generator --check-batch BATCH_ID -p openai --save-results
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
  "tips_dir": "/path/to/custom/tips",
  "categories": {
    "1": {"name": "proposed-new-module", "desc": "Proposed new module"},
    "35": {"name": "core-service", "desc": "Lesser-known core service"}
  }
}
```

### Tips Directory Configuration

The tips directory can be configured via (in priority order):

1. **CLI argument**: `--tips-dir /path/to/tips`
2. **Environment variable**: `TIPGEN_TIPS_DIR=/path/to/tips`
3. **Config file**: `"tips_dir": "/path/to/tips"` in `config.json`
4. **Default**: `tips/` folder in the package directory

To add or modify categories, edit `config.json` directly - no code changes needed.

## Development

### Running Tests

```bash
# Dry run to verify configuration
drupaltools-tip-generator -c 35 -n 1 -p openrouter --dry-run
```

## Validation

Validate generated tips for formatting issues, truncation, and quality:

```bash
# Validate a single file
drupaltools-tip-generator --validate --validate-file tips/core-service/a1b2c3d4.md

# Validate all tips in a category
drupaltools-tip-generator --validate --validate-category core-service

# Validate ALL tips across all categories
drupaltools-tip-generator --validate --validate-all
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
