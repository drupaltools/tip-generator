---
name: drupal-tip
description: Show a random "tip of the day" related to Drupal development and its ecosystem. Use this skill whenever the user asks for a tip, hint, or suggestion related to Drupal — e.g. "drupal tip", "give me a Drupal tip", "tip of the day", "surprise me with Drupal", "what should I learn today", or simply calls the skill by name. Also trigger when the user seems idle or asks for inspiration in a Drupal context.
license: GPL-2.0-or-later
compatibility: opencode
author: Drupal Tools Team <info@drupaltools.com>
metadata:
  homepage: https://github.com/drupaltools/tip-generator
  pypi: drupaltools-tip-generator
---

# Drupal Tip of the Day

Display one random tip from the pre-generated static database.

## Installation

### Option 1: Install via Python package (Recommended)

Install the Python package, then run the random tip command:

```bash
# Install the package
pip install drupaltools-tip-generator

# Get a random tip
drupaltools-tip-generator --random-tip
```

### Option 2: Install via skills CLI

```bash
# Install for OpenCode
npx skills add drupaltools/tip-generator --agent opencode
```

### Option 3: Manual installation

Copy this skill to your OpenCode skills directory:

```bash
# Project-local (recommended)
mkdir -p .agents/skills/drupal-tip
cp SKILL.md .agents/skills/drupal-tip/

# Or global
mkdir -p ~/.config/opencode/skills/drupal-tip
cp SKILL.md ~/.config/opencode/skills/drupal-tip/
```

## Instructions

1. Run this command to get a random tip:

```bash
drupaltools-tip-generator --random-tip
```

Or if running from the source directory:

```bash
cd ~/.claude/skills/drupal-tip && .venv/bin/python tip_generator.py --random-tip
```

2. Display the output exactly as returned (includes the tip text and any code blocks).

3. Optionally filter by category:

```bash
drupaltools-tip-generator --random-tip --tip-category core-service
```

4. After the tip, add:

`Want to explore this further or get another tip?`

---

## Available Categories

Use `--tip-category <name>` to filter by one of these folder names:

| Folder | Description |
|--------|-------------|
| case-study | Drupal showcases |
| code-example | Code examples |
| composer-trick | Composer tips |
| concept-explanation | Drupal concepts explained |
| core-bash-commands | Core CLI commands |
| core-service | Core services |
| di-best-practice | Dependency injection |
| drupal-history | Drupal history |
| drupal-hook | Hook examples |
| drupal-statistics | Statistics |
| drupal-vs-cms | CMS comparisons |
| form-api-advanced | Form API patterns |
| general-best-practices | Best practices |
| ide-tip | IDE tips |
| llm-prompt-idea | LLM prompts |
| multilingual | Multilingual tips |
| rare-ddev-command | DDEV commands |
| rare-drush-command | Drush commands |
| release-cycle | Release info |
| rephrased-quote | Famous quotes |
| song | Song parodies |
| symfony-internals | Symfony in Drupal |
| useful-composer-package | Composer packages |
| wikipedia-fact | Wikipedia facts |
| xdebug-xhprof | Debugging tools |

---

## Database Management

If you need to generate new tips (requires API keys):

```bash
# Install the package
pip install drupaltools-tip-generator

# Generate tips for a specific category
drupaltools-tip-generator -c 35 -n 5 -p openai

# Or generate for all categories
drupaltools-tip-generator -c all -n 3 -p openai
```

Or if running from source:

```bash
cd ~/.claude/skills/drupal-tip

# Install dependencies
pip install -e .

# Generate tips
python -c 35 -n 5 -p openai
```

Other commands:

```bash
# List all available category IDs
drupaltools-tip-generator --list-categories

# List categories with existing tips
drupaltools-tip-generator --list-existing

# Fetch remote data for categories with URLs (run before generating)
drupaltools-tip-generator --fetch-data

# Validate generated tips
drupaltools-tip-generator --validate --validate-all
```

Supported providers: `anthropic`, `openai`, `openrouter`
