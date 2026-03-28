# Agent Instructions for drupaltools-tip-generator

## Project Overview

CLI tool that generates static markdown tip files for Drupal development using LLM providers (Anthropic, OpenAI). Tips are generated for specific categories (hooks, cache API, Drush commands, etc.).

## Project Structure

```
.
├── config.json          # Categories, URLs, prompt template
├── src/tip_generator/
│   ├── __init__.py      # Main CLI, LLM integration, prompt building
│   ├── url_cache.py     # URL fetching, caching, sub-link extraction
│   └── viewer.py        # HTML preview server
├── tests/               # pytest tests
├── data/tips/           # Generated tip files (gitignored)
├── pyproject.toml       # Python package config
└── release.sh           # Tag + GitHub Release workflow
```

## Key Commands

```bash
# Generate tips for a category
drupaltools-tip-generator --category 42 --count 5 --provider openai

# Generate from category name
drupaltools-tip-generator --category cache-api --count 5 -p anthropic

# Generate all categories
drupaltools-tip-generator --all

# Batch mode (non-blocking)
drupaltools-tip-generator --category 42 --no-wait

# Download batch results
drupaltools-tip-generator --download-batch <batch_id>

# List pending batches
drupaltools-tip-generator --list-batches

# Fetch URLs for a category (pre-populate cache)
drupaltools-tip-generator --fetch-category 84

# Preview tips as HTML
drupaltools-tip-generator --serve

# Run tests
uv run pytest tests/ -v

# Release (bumps patch version, pushes tag)
./release.sh
```

## Categories

Categories are defined in `config.json`. Each category can have:
- `name`: machine name (used for filenames)
- `desc`: description for the LLM prompt
- `urls`: optional list of URLs to fetch and include as reference data

Categories with `urls` are automatically fetched and their content is injected into the prompt. The fetcher:
1. Extracts up to 20 sub-links from each URL
2. Detects pagination patterns (`?page=N`, `/page/N`)
3. Fetches up to 5 pagination pages
4. Caches everything to `~/.drupaltools/tip-generator/cache/url_cache/`

## Adding a New Category

1. Add entry to `config.json` under `categories`:
```json
"91": {
  "name": "my-new-category",
  "desc": "Description for the LLM",
  "urls": ["https://optional-reference-url.com"]  // optional
}
```

2. Test generation:
```bash
drupaltools-tip-generator --category 91 --count 1
```

## Prompt Template

The `prompt_template` in `config.json` defines the base prompt. Variables available:
- `{cat_id}` — category number
- `{cat_name}` — category machine name
- `{cat_desc}` — category description

Reference data from URLs is appended automatically with the header "Here is some reference data you can use:".

## Code Style

- Python 3.11+
- Use type hints
- No trailing whitespace
- Max line length: 88 (Black default)
- Docstrings only for complex public APIs

## Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_url_cache.py -v

# Run with coverage
uv run pytest --cov=tip_generator tests/
```

## Release Process

1. `./release.sh` — bumps patch version, creates git tag, pushes
2. GitHub Actions triggers:
   - `release.yml` — creates GitHub Release
   - `publish.yml` — runs tests, builds wheel, publishes to PyPI

Version is injected into `pyproject.toml` by `publish.yml` via `sed` (do not hardcode versions there).

## Environment

- `TIPGEN_CONFIG_FILE` — path to custom config.json
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` — API keys for LLM providers
- `OPENAI_API_URL` / `ANTHROPIC_API_URL` — custom API endpoints (for proxies)

## Common Issues

**Cache not populating**: Run `drupaltools-tip-generator --fetch-category <N>` to debug URL fetching.

**Tests failing**: Check if dependencies are installed: `uv sync --all-extras`.

**PyPI publish fails**: Ensure version doesn't already exist on PyPI. Bump version in `release.sh`.
