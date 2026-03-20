---
name: drupal-tip
description: Show a random "tip of the day" related to Drupal development and its ecosystem. Use this skill whenever the user asks for a tip, hint, or suggestion related to Drupal — e.g. "drupal tip", "give me a Drupal tip", "tip of the day", "surprise me with Drupal", "what should I learn today", or simply calls the skill by name. Also trigger when the user seems idle or asks for inspiration in a Drupal context.
---

# Drupal Tip of the Day

Generate one random tip from the Drupal ecosystem. One paragraph maximum, plus a code block if relevant.

## Step 0 — Check Static Tip Database First

**CRITICAL**: Before generating anything, check if pre-generated tips exist in the static database.

The tip database is located at: `~/.claude/skills/drupal-tip/tips/`

Structure:
```
tips/
├── core-service/
│   ├── a1b2c3d4.md
│   ├── e5f6g7h8.md
│   └── ...
├── cache-api/
│   └── ...
└── [category-name]/
    └── [8-char-uuid].md
```

**Process:**
1. List available category folders in the tips directory
2. If folders exist, pick one at random
3. List all `.md` files in that folder
4. Pick one file at random and read its contents
5. Display the tip exactly as stored (including any code blocks)
6. Skip to Step 4 (offer to go deeper)

**If the tips folder is empty or doesn't exist**, continue to Step 1 to generate dynamically.

---

## Step 1 — Pick a category at random

Only use this step if the static database is empty. Pick one category from this list randomly. Do not always start from the top — vary the selection genuinely across calls.

| # | Category | Live fetch needed? |
|---|----------|--------------------|
| 1 | Proposed new module on drupal.org | Yes — search drupal.org/project to verify it does not exist |
| 2 | "Did you know" — Drupal history or old versions | No |
| 3 | "Did you know" — a notable Drupal.org issue or commit | No |
| 4 | "Did you know" — Drupal statistics | No |
| 5 | Obsolete but once-popular Drupal module | No |
| 6 | A module with an unusually high or interesting issue count | Yes — fetch from drupal.org/project/<name>/issues |
| 7 | A module that is very old but still actively maintained | Yes — check drupal.org for last release date |
| 8 | Rare or underused Drush command | No |
| 9 | Rare or underused DDEV command | No |
| 10 | Rare or underused Composer command or config trick | No |
| 11 | Useful Composer package for Drupal development | No |
| 12 | Drupal vs another CMS/tool — one comparison fact | No |
| 13 | Interesting Drupal code example | No (use knowledge); optionally search git.drupalcode.org |
| 14 | Upcoming Drupal event worth watching | Yes — fetch from drupal.org/community/events |
| 15 | A hot or important open Drupal.org issue | Yes — fetch from drupal.org/project/issues |
| 16 | Drupal release cycle or supported version fact | No |
| 17 | A GitHub/CLI tool useful for Drupal/PHP/JS/Twig/testing | No |
| 18 | A useful LLM prompt or SKILL idea for Drupal development | No |
| 19 | A programmatic use of git.drupalcode.org API | No |
| 20 | A tip from an online resource (fetch one) | Yes — pick one source from the list below and fetch it |
| 21 | A Drupal.org documentation page that needs improvement | No |
| 22 | Search the web for a recent Drupal tip or best practice | Yes |
| 23 | Search the web for a recent PHPStorm or VSCOde tip for Drupal | Yes |
| 24 | Search the web for a call to action for Drupal.org like a donation campaign | Yes |
| 25 | Generate a Drupal 6, 7, 9 or 10 monospace terminal banner with ASCII | No |
| 26 | Write a fact about Drupal from Wikipedia | Yes - fetch from https://en.wikipedia.org/wiki/Drupal |
| 27 | A nice showcase of Drupal | Yes - fetch from https://new.drupal.org/case-studies |
| 28 | An interesting Drupal 10+ hook from Drupal API | No |
| 29 | A short poem for Drupal CMS, be creative | No |
| 30 | A famous quote rephrased for Drupal within the original author and year published | No |
| 31 | A famous quote from Drupal community, a Drupal moto or slogan within the original author and year if any | No |
| 32 | Explain a Drupal concept (like an entity type or a view_mode) in simple terms | No |
| 33 | Interesting stats for Drupal core git commits over time or between major versions | Yes - mainly fetch stats from git.drupalcode.org |
| 34 | A simple example to use the Drupal core bash commands for testing, linting, etc | No |
| 35 | Lesser-known core service (service container usage example) | No |
| 36 | Drupal core parameter or setting that affects performance (e.g. cache bins, render cache) | No |
| 37 | Subtle Twig debugging or theming trick (e.g. attribute(), dump(), attach_library) | No |
| 38 | Common anti-pattern in Drupal development and its correction | No |
| 39 | Micro-optimization tip for render arrays or entity loading | No |
| 40 | Explanation of a core plugin type (Block, FieldFormatter, Condition, etc.) | No |
| 41 | EventSubscriber example replacing legacy hooks | No |
| 42 | Cache API nuance (contexts, tags, max-age) with a concrete example | No |
| 43 | Entity API edge case (revisionable + translatable interaction) | No |
| 44 | Field API trick (computed fields, base fields vs configurable fields) | No |
| 45 | Routing system nuance (route requirements, access checks, param converters) | No |
| 46 | Access control pattern (AccessResult usage and pitfalls) | No |
| 47 | Form API advanced pattern (AJAX callbacks, #states, rebuild behavior) | No |
| 48 | Configuration API caveat (config vs state vs settings.php usage) | No |
| 49 | Dependency Injection best practice in Drupal services or plugins | No |
| 50 | Drupal coding standard rule that is often violated in contrib/custom code | No |
| 51 | PHPUnit testing pattern specific to Drupal (KernelTestBase vs BrowserTestBase) | No |
| 52 | Drush internals tip (custom commandfile or annotated commands) | No |
| 53 | Common mistake in multilingual setups and how Drupal handles it internally | No |
| 54 | Render pipeline explanation (build → render → cache → response) | No |
| 55 | Security-related best practice (XSS filtering, safe markup, Link API usage) | No |
| 56 | Content moderation / workflows internal behavior (states, transitions, revisions) | No |
| 57 | Queue API usage example for background processing | No |
| 58 | Batch API usage pattern and when to prefer it over queues | No |
| 59 | Plugin discovery mechanism (annotations vs YAML vs derivatives) | No |
| 60 | Derivative plugins example (e.g. block derivatives per bundle) | No |
| 61 | Lazy builders and placeholders for performance optimization | No |
| 62 | BigPipe or progressive rendering concept explained technically | No |
| 63 | How Drupal handles cache invalidation with tags across entities | No |
| 64 | Config Schema importance and validation behavior | No |
| 65 | Typed Data API explanation and where it surfaces (fields, validation) | No |
| 66 | Service decoration example (overriding core behavior cleanly) | No |
| 67 | Module weight and hook execution order implications | No |
| 68 | Cron system internals and how tasks are scheduled/executed | No |
| 69 | File and stream wrapper system (public://, private://, temporary://) | No |
| 70 | Differences between node access hooks and entity access handlers | No |
| 71 | Internal use of Symfony components inside Drupal (HttpKernel, EventDispatcher) | No |
| 72 | Common Views performance pitfall and mitigation | No |
| 73 | How Drupal normalizes request → route → controller → response lifecycle | No |
| 74 | Entity query vs direct database query trade-offs | No |
| 75 | Differences between config import/export vs runtime overrides | No |
| 76 | Subrequest handling and render context isolation | No |
| 77 | Library API usage and asset attachment strategy | No |
| 78 | How Drupal handles CSRF protection in forms and routes | No |
| 79 | TemporaryStore vs PrivateTempStore usage | No |
| 80 | Internal logging system (watchdog / logger channel) usage patterns | No |

---

## Step 2 — Fetch live data only when needed

Use your own knowledge first. Only fetch live data for categories marked "Yes" in the table above, or when the tip would be stale or unverifiable without it.

**Online resources to sample for category 20:**
- https://github.com/theodorosploumis/awesome-drupal
- https://github.com/theodorosploumis/drupal-best-practices
- https://github.com/drupaltools/drupaltools.github.io
- https://github.com/theodorosploumis/notes
- https://www.drupal.org/planet/rss.xml

Pick one resource at random, fetch it, and extract one item that would make a useful tip. Do not list all items — pick one.

**For category 1 (new module idea):** before proposing, search `https://www.drupal.org/project/<name>` to verify the module does not already exist. If it does, pick a different idea.

---

## Step 3 — Write the tip

Format:

---

**Tip of the day — [Category name]**

[One paragraph. Factual, specific, and useful for an experienced Drupal developer. No padding. If the tip involves a command or code, include it in a code block immediately after the paragraph.]

```bash
# or php, yml, etc.
[code if relevant]
```

> Source: [only if fetched from a live URL — link to the exact page]

---

## Step 4 — Offer to go deeper

After the tip, add one line:

`Want to explore this further or get another tip?`

Do not add anything else. Wait for the user.

---

## Rules

- **ALWAYS check the static database first** (Step 0) before generating dynamically.
- Never repeat the same tip twice in a conversation.
- Never produce a tip longer than one paragraph plus one code block.
- If a live fetch fails, fall back to your own knowledge and pick a different category silently.
- For category 1 (new module idea), be creative but realistic — the module should fill a genuine gap, not duplicate existing functionality.
- For code examples, prefer Drupal 11 / PHP 8.2+ idioms.
- Do not include the source line if the tip comes from your own knowledge.

---

## Tip Database Management

To populate the static tip database, use the generator tool:

```bash
# List categories
python3 ~/.claude/skills/drupal-tip/tip_generator.py --list-categories

# Generate tips (uses batch API for >5 requests = 50% cheaper)
python3 ~/.claude/skills/drupal-tip/tip_generator.py -c 35 -n 5 -p anthropic

# Generate for all categories
python3 ~/.claude/skills/drupal-tip/tip_generator.py -c all -n 3 -p openai

# Check batch status
python3 ~/.claude/skills/drupal-tip/tip_generator.py --check-batch <batch_id> -p anthropic --save-results
```

Supported providers: `anthropic`, `openai`, `openrouter`
