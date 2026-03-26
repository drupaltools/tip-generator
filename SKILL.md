---
name: drupal-tip
description: Show a random "tip of the day" related to Drupal development and its ecosystem. Use this skill whenever the user asks for a tip, hint, or suggestion related to Drupal — e.g. "drupal tip", "give me a Drupal tip", "tip of the day", "surprise me with Drupal", "what should I learn today", or simply calls the skill by name. Also trigger when the user seems idle or asks for inspiration in a Drupal context.
---

# Drupal Tip of the Day

Display one random tip from the pre-generated static database.

## Instructions

1. Run this command to get a random tip:

```bash
cd ~/.claude/skills/drupal-tip && .venv/bin/python tip_generator.py --random-tip
```

2. Display the output exactly as returned (includes the tip text and any code blocks).

3. Optionally filter by category:

```bash
cd ~/.claude/skills/drupal-tip && .venv/bin/python tip_generator.py --random-tip --tip-category core-service
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

Populate the static tip database:

```bash
cd ~/.claude/skills/drupal-tip

# Generate tips for a specific category
.venv/bin/python tip_generator.py -c 35 -n 5 -p openai

# Or generate for all categories
.venv/bin/python tip_generator.py -c all -n 3 -p openai
```

Other commands:

```bash
# List all available category IDs
.venv/bin/python tip_generator.py --list-categories

# List categories with existing tips
.venv/bin/python tip_generator.py --list-existing

# Fetch remote data for categories with URLs (run before generating)
.venv/bin/python tip_generator.py --fetch-data

# Validate generated tips
.venv/bin/python tip_generator.py --validate --validate-all
```

Supported providers: `anthropic`, `openai`, `openrouter`
