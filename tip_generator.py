#!/usr/bin/env python3
"""
Drupal Tip Generator - Generate static MD files for the drupal-tip skill.

Usage:
    python tip_generator.py --random-tip              # Get a random existing tip (fast!)
    python tip_generator.py --category 35 --count 5 --provider anthropic
    python tip_generator.py --category all --count 3 --provider openai
    python tip_generator.py --list-categories

Supports batch APIs for cost savings:
- Anthropic: 50% discount, results within 24h (usually minutes)
- OpenAI: 50% discount, results within 24h
- OpenRouter: Varies by model

API Keys & Models: Set in .env file in this directory, or via environment variables, or --api-key / --model
"""

import argparse
import os
import json
import re
import time
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

# Load .env file from script directory
SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"


def load_env_file():
    """Load environment variables from .env file in script directory.

    All variables in .env should use TIPGEN_ prefix to avoid overriding
    global environment variables.
    """
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    os.environ[key] = value


# Load .env on import
load_env_file()


def get_env(key: str, default: str = None) -> Optional[str]:
    """Get env var, checking TIPGEN_ prefix first, then global."""
    return os.environ.get(f"TIPGEN_{key}") or os.environ.get(key, default)


# Default models per provider (can be overridden in .env)
DEFAULT_MODELS = {
    "anthropic": get_env("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
    "openai": get_env("OPENAI_MODEL", "gpt-5.4-mini"),
    "openrouter": get_env("OPENROUTER_MODEL", "openai/gpt-5.1-codex-mini"),
}


def get_default_model(provider: str) -> str:
    """Get default model for provider from env or hardcoded fallback."""
    return DEFAULT_MODELS.get(provider, "unknown")


# Try to import LLM libraries
try:
    import anthropic

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

# Import url_cache for remote content fetching
try:
    from url_cache import (
        extract_urls,
        fetch_category_urls,
        fetch_all_category_data,
        build_context_for_category,
    )

    HAS_URL_CACHE = True
except ImportError:
    HAS_URL_CACHE = False

try:
    from openai import OpenAI

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# Config file path
CONFIG_FILE = SCRIPT_DIR / "config.json"


def load_config() -> dict:
    """Load configuration from JSON file."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_FILE}")
    with open(CONFIG_FILE) as f:
        return json.load(f)


# Load config
CONFIG = load_config()

# Convert categories from string keys to int keys for backward compatibility
CATEGORIES = {int(k): v for k, v in CONFIG["categories"].items()}

TIPS_DIR = SCRIPT_DIR / "tips"


def get_prompt_for_category(
    cat_id: int, cat_info: dict, include_context: bool = True
) -> str:
    """Generate a prompt for a specific category using the template from config."""
    template = CONFIG.get("prompt_template", "")

    context = ""
    if include_context and HAS_URL_CACHE:
        context = build_context_for_category(cat_id, cat_info)

    prompt = template.format(
        cat_id=cat_id, cat_desc=cat_info["desc"], cat_name=cat_info["name"]
    )

    if context:
        prompt = f"{prompt}\n\nHere is some reference data you can use:\n\n{context}"

    return prompt


def generate_file_id() -> str:
    """Generate an 8-character lowercase random ID."""
    return uuid.uuid4().hex[:8]


def save_tip(cat_info: dict, content: Optional[str]) -> Optional[Path]:
    """Save a tip to the appropriate file."""
    if not content:
        return None

    category_dir = TIPS_DIR / cat_info["name"]
    category_dir.mkdir(parents=True, exist_ok=True)

    file_id = generate_file_id()
    file_path = category_dir / f"{file_id}.md"

    # Extract frontmatter if present, then strip it
    title = ""
    body = content.strip()
    if body.startswith("---"):
        parts = body.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            body = parts[2].strip()
            # Extract title from existing frontmatter
            for line in fm_text.split("\n"):
                if line.strip().startswith("title:"):
                    title = line.split("title:", 1)[1].strip()
                    break

    frontmatter = f"""---
category: {cat_info["name"]}
generated: {datetime.now().isoformat()}
"""
    if title:
        frontmatter += f"title: {title}\n"
    frontmatter += "---\n\n"

    with open(file_path, "w") as f:
        f.write(frontmatter + body)

    return file_path


# ============ BATCH API FUNCTIONS ============


def anthropic_batch_create(requests: List[dict], api_key: str) -> str:
    """Create an Anthropic batch and return the batch ID."""
    client = anthropic.Anthropic(
        api_key=api_key,
        default_headers={"anthropic-beta": "message-batches-2024-09-24"},
    )

    batch_requests = []
    for req in requests:
        batch_requests.append(
            {
                "custom_id": req.get("custom_id", str(uuid.uuid4())),
                "params": {
                    "model": req.get("model") or get_default_model("anthropic"),
                    "max_tokens": 2048,
                    "messages": [{"role": "user", "content": req["prompt"]}],
                },
            }
        )

    batch = client.messages.batches.create(requests=batch_requests)
    return batch.id


def anthropic_batch_check(batch_id: str, api_key: str) -> dict:
    """Check Anthropic batch status and return results if complete."""
    client = anthropic.Anthropic(api_key=api_key)
    batch = client.messages.batches.retrieve(batch_id)

    result = {
        "status": batch.processing_status,
        "complete": batch.processing_status == "ended",
        "results": [],
    }

    if result["complete"]:
        # Get results
        for res in client.messages.batches.results(batch_id):
            if res.result.type == "succeeded":
                result["results"].append(
                    {
                        "custom_id": res.custom_id,
                        "content": res.result.message.content[0].text,
                    }
                )

    return result


def openai_batch_create(requests: List[dict], api_key: str, model: str = None) -> str:
    """Create an OpenAI batch and return the batch ID."""
    client = OpenAI(api_key=api_key)
    model = model or get_default_model("openai")

    # Create JSONL file content
    jsonl_content = ""
    for req in requests:
        jsonl_content += (
            json.dumps(
                {
                    "custom_id": req.get("custom_id", str(uuid.uuid4())),
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": model,
                        "max_completion_tokens": 2048,
                        "messages": [{"role": "user", "content": req["prompt"]}],
                    },
                }
            )
            + "\n"
        )

    # Upload file
    batch_file = client.files.create(
        file=jsonl_content.encode("utf-8"), purpose="batch"
    )

    # Create batch
    batch = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
    )

    return batch.id


def openai_batch_check(batch_id: str, api_key: str) -> dict:
    """Check OpenAI batch status and return results if complete."""
    client = OpenAI(api_key=api_key)
    batch = client.batches.retrieve(batch_id)

    result = {
        "status": batch.status,
        "complete": batch.status in ["completed", "failed", "expired"],
        "results": [],
        "errors": [],
    }

    if batch.status == "failed":
        result["error"] = (
            getattr(batch, "error", None) or f"Batch failed with status: {batch.status}"
        )
        result["errors"] = getattr(batch, "errors", []) or []

    if batch.status == "completed" and batch.output_file_id:
        file_content = client.files.content(batch.output_file_id)
        for line in file_content.text.strip().split("\n"):
            if not line:
                continue
            data = json.loads(line)
            response_status = data.get("response", {}).get("status_code")
            if response_status == 200:
                body = data["response"]["body"]
                result["results"].append(
                    {
                        "custom_id": data["custom_id"],
                        "content": body["choices"][0]["message"]["content"],
                    }
                )
            else:
                error_msg = f"{data.get('custom_id', 'unknown')}: {data.get('response', {}).get('body', {}).get('error', {}).get('message', 'Unknown error')}"
                result["errors"].append(error_msg)

    return result


def openrouter_batch_check(batch_id: str, api_key: str) -> dict:
    """Check OpenRouter batch status and return results if complete."""
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/drupaltools/drupal-tip-generator",
            "X-OpenRouter-Title": "Drupal Tip Generator",
            "X-OpenRouter-Categories": "cli-agent",
        },
    )
    batch = client.batches.retrieve(batch_id)

    result = {
        "status": batch.status,
        "complete": batch.status in ["completed", "failed", "expired"],
        "results": [],
    }

    if batch.status == "completed" and batch.output_file_id:
        # Get results
        file_content = client.files.content(batch.output_file_id)
        for line in file_content.text.strip().split("\n"):
            data = json.loads(line)
            if data.get("response", {}).get("status_code") == 200:
                body = data["response"]["body"]
                result["results"].append(
                    {
                        "custom_id": data["custom_id"],
                        "content": body["choices"][0]["message"]["content"],
                    }
                )

    return result


def openrouter_batch_create(
    requests: List[dict], api_key: str, model: str = None
) -> str:
    """Create an OpenRouter batch - uses OpenAI-compatible API with OpenRouter base URL."""
    model = model or get_default_model("openrouter")
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/drupaltools/drupal-tip-generator",
            "X-OpenRouter-Title": "Drupal Tip Generator",
            "X-OpenRouter-Categories": "cli-agent",
        },
    )

    # Create JSONL file content
    jsonl_content = ""
    for req in requests:
        jsonl_content += (
            json.dumps(
                {
                    "custom_id": req.get("custom_id", str(uuid.uuid4())),
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": model,
                        "max_completion_tokens": 2048,
                        "messages": [{"role": "user", "content": req["prompt"]}],
                    },
                }
            )
            + "\n"
        )

    # Upload file
    batch_file = client.files.create(
        file=jsonl_content.encode("utf-8"), purpose="batch"
    )

    # Create batch
    batch = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
    )

    return batch.id


# ============ SYNC API FUNCTIONS ============


def call_anthropic_sync(prompt: str, api_key: str, model: str = None) -> dict:
    """Call Anthropic API synchronously."""
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model or get_default_model("anthropic"),
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return {
        "content": message.content[0].text,
        "finish_reason": message.stop_reason,  # "end_turn" or "max_tokens"
    }


def call_openai_sync(prompt: str, api_key: str, model: str = None) -> dict:
    """Call OpenAI API synchronously."""
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model or get_default_model("openai"),
        max_completion_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    choice = response.choices[0]
    content = choice.message.content
    if content is None:
        raise ValueError(
            f"Model returned empty content (finish_reason: {choice.finish_reason})"
        )

    return {
        "content": content,
        "finish_reason": choice.finish_reason,
    }


def call_openrouter_sync(prompt: str, api_key: str, model: str = None) -> dict:
    """Call OpenRouter API synchronously."""
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/drupaltools/drupal-tip-generator",
            "X-OpenRouter-Title": "Drupal Tip Generator",
            "X-OpenRouter-Categories": "cli-agent",
        },
    )
    response = client.chat.completions.create(
        model=model or get_default_model("openrouter"),
        max_completion_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    choice = response.choices[0]
    content = choice.message.content
    finish_reason = choice.finish_reason

    if content is None:
        raise ValueError(
            f"Model returned empty content (finish_reason: {finish_reason})"
        )

    return {
        "content": content,
        "finish_reason": finish_reason,
    }


# ============ GENERATION FUNCTIONS ============

ERROR_LOG_FILE = SCRIPT_DIR / "errors.json"


def log_error(error_data: dict) -> None:
    """Log an error to the errors.json file."""
    errors = []
    if ERROR_LOG_FILE.exists():
        try:
            with open(ERROR_LOG_FILE) as f:
                errors = json.load(f)
        except (json.JSONDecodeError, IOError):
            errors = []

    errors.append(error_data)

    with open(ERROR_LOG_FILE, "w") as f:
        json.dump(errors, f, indent=2)


def generate_sync(
    categories: List[int], count: int, provider: str, api_key: str, model: Optional[str]
) -> int:
    """Generate tips synchronously (one at a time)."""
    generated = 0
    truncated = 0

    for cat_id in categories:
        if cat_id not in CATEGORIES:
            print(f"Warning: Category {cat_id} not found, skipping")
            continue

        cat_info = CATEGORIES[cat_id]
        print(f"\nCategory {cat_id}: {cat_info['desc']}")

        for i in range(count):
            prompt = get_prompt_for_category(cat_id, cat_info)

            print(f"  Generating tip {i + 1}/{count}...", end=" ", flush=True)

            try:
                if provider == "anthropic":
                    tip_data = call_anthropic_sync(
                        prompt, api_key, model or get_default_model("anthropic")
                    )
                elif provider == "openai":
                    tip_data = call_openai_sync(
                        prompt, api_key, model or get_default_model("openai")
                    )
                elif provider == "openrouter":
                    tip_data = call_openrouter_sync(
                        prompt, api_key, model or get_default_model("openrouter")
                    )
                else:
                    raise ValueError(f"Unknown provider: {provider}")

                # Check for truncation
                finish_reason = tip_data.get("finish_reason", "unknown")
                if finish_reason in ("length", "max_tokens"):
                    print(f"TRUNCATED ({finish_reason})")
                    truncated += 1
                    log_error(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "category_id": cat_id,
                            "category_name": cat_info.get("name"),
                            "tip_number": i + 1,
                            "provider": provider,
                            "model": model or get_default_model(provider),
                            "error": f"Response truncated (finish_reason: {finish_reason})",
                            "content": tip_data.get("content", "")[
                                :500
                            ],  # First 500 chars for debugging
                        }
                    )
                    continue

                file_path = save_tip(cat_info, tip_data.get("content"))
                if not file_path:
                    print("ERROR: Empty response content, skipping")
                    log_error(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "category_id": cat_id,
                            "category_name": cat_info.get("name"),
                            "tip_number": i + 1,
                            "provider": provider,
                            "model": model or get_default_model(provider),
                            "error": "Empty response content",
                        }
                    )
                    continue
                print(f"Saved to {file_path.relative_to(SCRIPT_DIR)}")
                generated += 1

            except Exception as e:
                print(f"Error: {e}")
                log_error(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "category_id": cat_id,
                        "category_name": cat_info.get("name"),
                        "tip_number": i + 1,
                        "provider": provider,
                        "model": model or get_default_model(provider),
                        "error": str(e),
                    }
                )

    if truncated > 0:
        print(
            f"\nWarning: {truncated} tips were truncated and not saved (see errors.json)"
        )

    return generated


def generate_batch(
    categories: List[int],
    count: int,
    provider: str,
    api_key: str,
    model: Optional[str],
    wait: bool = True,
) -> int:
    """Generate tips using batch API (50% cheaper)."""
    requests = []

    for cat_id in categories:
        if cat_id not in CATEGORIES:
            print(f"Warning: Category {cat_id} not found, skipping")
            continue

        cat_info = CATEGORIES[cat_id]

        for i in range(count):
            prompt = get_prompt_for_category(cat_id, cat_info)
            requests.append(
                {
                    "custom_id": f"{cat_info['name']}_{i + 1}",
                    "prompt": prompt,
                    "model": model,
                }
            )

    if not requests:
        print("No requests to process")
        return 0

    print(f"Creating batch with {len(requests)} requests...")

    try:
        if provider == "anthropic":
            batch_id = anthropic_batch_create(requests, api_key)
        elif provider == "openai":
            batch_id = openai_batch_create(
                requests, api_key, model or get_default_model("openai")
            )
        elif provider == "openrouter":
            batch_id = openrouter_batch_create(
                requests, api_key, model or get_default_model("openrouter")
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

        print(f"Batch created: {batch_id}")
        print(
            f"Check status with: python tip_generator.py --check-batch {batch_id} -p {provider}"
        )

        if not wait:
            return 0

        # Poll for completion
        print("\nWaiting for batch to complete...")
        while True:
            if provider == "anthropic":
                result = anthropic_batch_check(batch_id, api_key)
            elif provider == "openrouter":
                result = openrouter_batch_check(batch_id, api_key)
            else:
                result = openai_batch_check(batch_id, api_key)

            print(f"  Status: {result['status']}")

            if result["complete"]:
                if result["status"] in ("failed", "expired"):
                    error_msg = f"Batch {result['status']}: {result.get('error', 'Unknown error')}"
                    print(f"\nERROR: {error_msg}")
                    log_error(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "batch_id": batch_id,
                            "provider": provider,
                            "error": error_msg,
                            "type": "batch_failed",
                        }
                    )
                    return 0

                print(
                    f"\nBatch complete! Processing {len(result['results'])} results..."
                )

                if result.get("errors"):
                    print(f"\n{len(result['errors'])} request(s) failed:")
                    for err in result["errors"]:
                        print(f"  - {err}")
                    log_error(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "batch_id": batch_id,
                            "provider": provider,
                            "error": "Individual request failures",
                            "errors": result["errors"],
                            "type": "batch_partial_failure",
                        }
                    )

                generated = 0
                for res in result["results"]:
                    custom_id = res["custom_id"]
                    cat_name = custom_id.rsplit("_", 1)[0]
                    cat_info = next(
                        (c for c in CATEGORIES.values() if c["name"] == cat_name), None
                    )

                    if cat_info:
                        file_path = save_tip(cat_info, res.get("content"))
                        if file_path:
                            print(f"  Saved: {file_path.relative_to(SCRIPT_DIR)}")
                            generated += 1
                        else:
                            print(f"  SKIPPED: Empty content for {custom_id}")

                return generated

            time.sleep(10)

    except Exception as e:
        print(f"Batch error: {e}")
        return 0


def check_batch_status(
    batch_id: str, provider: str, api_key: str, save: bool = False
) -> None:
    """Check batch status and optionally save results."""
    print(f"Checking batch {batch_id}...")

    try:
        if provider == "anthropic":
            result = anthropic_batch_check(batch_id, api_key)
        elif provider == "openrouter":
            result = openrouter_batch_check(batch_id, api_key)
        else:
            result = openai_batch_check(batch_id, api_key)

        print(f"Status: {result['status']}")
        print(f"Complete: {result['complete']}")
        print(f"Results: {len(result['results'])}")

        if result["complete"] and save and result["results"]:
            print("\nSaving results...")
            for res in result["results"]:
                custom_id = res["custom_id"]
                cat_name = custom_id.rsplit("_", 1)[0]
                cat_info = next(
                    (c for c in CATEGORIES.values() if c["name"] == cat_name), None
                )

                if cat_info:
                    file_path = save_tip(cat_info, res.get("content"))
                    if file_path:
                        print(f"  Saved: {file_path.relative_to(SCRIPT_DIR)}")
                    else:
                        print(f"  SKIPPED: Empty content for {custom_id}")

    except Exception as e:
        print(f"Error: {e}")


def list_categories():
    """List all available categories."""
    print("Available categories:\n")
    for cat_id, info in CATEGORIES.items():
        print(f"  {cat_id:2d}. {info['desc']}")
    print(f"\nTotal: {len(CATEGORIES)} categories")
    print("\nUse 'all' as category to generate for all categories")


# ============ RANDOM TIP RETRIEVAL ============


def get_all_tip_files() -> List[Path]:
    """Get all .md tip files from all category directories."""
    if not TIPS_DIR.exists():
        return []
    return list(TIPS_DIR.rglob("*.md"))


def get_random_tip() -> Optional[Path]:
    """Pick and return a random tip file path."""
    files = get_all_tip_files()
    if not files:
        return None
    import random

    return random.choice(files)


def print_random_tip(category: Optional[str] = None) -> bool:
    """
    Print a random tip from the database.

    Args:
        category: Optional category name to filter by. If None, picks from any category.

    Returns:
        True if a tip was found and printed, False otherwise.
    """
    if not TIPS_DIR.exists():
        print("No tips directory found. Generate tips first with --category.")
        return False

    if category:
        cat_dir = TIPS_DIR / category
        if not cat_dir.exists():
            print(f"Category '{category}' not found in tips database.")
            print(f"\nTo add tips for this category:")
            print(
                f"  1. Check if it exists in config.json: python tip_generator.py --list-categories"
            )
            print(
                f"  2. Generate tips: python tip_generator.py -c <category-id> -n 5 -p openrouter"
            )
            print(f"\nExisting categories:")
            list_existing_categories()
            return False
        files = list(cat_dir.glob("*.md"))
        if not files:
            print(f"Category '{category}' exists but has no tips yet.")
            print(f"Generate tips: python tip_generator.py -c <id> -n 5 -p openrouter")
            return False
    else:
        files = get_all_tip_files()
        if not files:
            print("No tips found in database.")
            return False

    import random

    tip_file = random.choice(files)

    with open(tip_file) as f:
        content = f.read()

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2].strip()

    print(content.strip())
    return True


def list_existing_categories() -> None:
    """List categories that have tips in the database."""
    if not TIPS_DIR.exists():
        print("No tips directory found.")
        return

    categories = [d.name for d in TIPS_DIR.iterdir() if d.is_dir()]
    if not categories:
        print("No tip categories found.")
        return

    print("Existing tip categories:")
    for cat in sorted(categories):
        count = len(list((TIPS_DIR / cat).glob("*.md")))
        print(f"  {cat}: {count} tip(s)")


# ============ TIP VALIDATION ============


class TipValidator:
    """Validates generated tip markdown files."""

    # Drupal API patterns that should exist if mentioned
    DRUPAL_API_PATTERNS = [
        r"\\Drupal::",
        r"\\\\Drupal\\\\",
        r"::service\(",
        r"\\Drupal\\\\[a-zA-Z]+Interface",
        r"::get\(",
        r"::set\(",
        r"::save\(",
        r"::load\(",
        r"#[\w-]+",
        r"@\\Drupal",
    ]

    # Common hallucinated Drupal functions/classes (should not exist)
    FAKE_PATTERNS = [
        r"Drupal\s*::\s*generateUUID",  # Fake static method
        r"Drupal\s*::\s*createEntity",  # Non-existent
        r"Drupal\\\\Core\\\\Entity\\\\FakeEntity",  # Made-up class
        r"\\\\Drupal\\\\Fake\\\\FakeService",  # Non-existent service
        r"Drupal\s*::\s*cache\s*\(\s*\)",  # Fake cache method
        r"node_load_multiple\s*\(\s*\$ids\s*\)",  # Wrong signature
    ]

    TRUNCATION_PATTERNS = [
        r"\.\.\.$",
        r"\[TODO\]",
        r"\[TBD\]",
        r"\[insert.*\]",
        r"<undefined>",
        r"NULL\n",
        r"unset\(",
        r"\$[\w]+->[\w]+$",
    ]

    # Known Drupal core services (partial list for validation)
    KNOWN_SERVICES = {
        "database",
        "entity_type.manager",
        "entity.query",
        "entity.manager",
        "cache.default",
        "cache.render",
        "cache.bootstrap",
        "path_alias.manager",
        "path_alias.repository",
        "plugin.manager.block",
        "plugin.manager.field",
        "logger.factory",
        "mail.manager",
        "state",
        "config.factory",
        "keyvalue",
        "temporary_store",
        "private_tempstore",
        "renderer",
        "theme.manager",
        "theme.registry",
        "router.builder",
        "access_manager",
        "current_user",
        "authentication",
        "csrf_token",
        "url_generator",
        "link_generator",
        "entity_type.repository",
        "entity_display.repository",
        "string_translation",
        "translation",
        "module_handler",
        "theme_handler",
        "extension.path.resolver",
    }

    # Known Drush commands
    KNOWN_DRUSH = {
        "drush cr",
        "drush cc",
        "drush cache-clear",
        "drush updb",
        "drush cim",
        "drush cex",
        "drush cim",
        "drush cim",
        "drush cr",
        "drush core-requirements",
        "drush core:requirements",
        "drush gen",
        "drush generate",
        "drush php:eval",
        "drush php-script",
        "drush site:install",
        "drush si",
        "drush uwd",
        "drush user:watchdog",
        "drush ws",
        "drush watchdog:show",
        "drush config-set",
        "drush cset",
        "drush config-get",
        "drush cget",
        "drush state-set",
        "drush sset",
    }

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.content = ""
        self.frontmatter = {}
        self.body = ""
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def parse(self) -> bool:
        try:
            with open(self.file_path) as f:
                self.content = f.read()
        except Exception as e:
            self.errors.append(f"Failed to read file: {e}")
            return False

        if not self.content.strip():
            self.errors.append("File is empty")
            return False

        if self.content.startswith("---"):
            parts = self.content.split("---", 2)
            if len(parts) < 3:
                self.errors.append("Malformed frontmatter: missing closing ---")
                return False

            fm_text = parts[1]
            self.body = parts[2].strip()

            current_key = None
            current_value = ""
            for line in fm_text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if ":" in line:
                    if current_key:
                        self.frontmatter[current_key] = current_value.strip()
                    parts_line = line.split(":", 1)
                    current_key = parts_line[0].strip()
                    current_value = parts_line[1].strip() if len(parts_line) > 1 else ""
            if current_key:
                self.frontmatter[current_key] = current_value.strip()

            if "category" in self.frontmatter and "title" not in self.frontmatter:
                cat_val = self.frontmatter["category"]
                if "title:" in cat_val:
                    parts = cat_val.split("title:", 1)
                    self.frontmatter["category"] = parts[0].strip().rstrip(":")
                    self.frontmatter["title"] = parts[1].strip()
                elif "title" in cat_val.lower():
                    self.warnings.append(
                        "Malformed frontmatter: category and title may be merged"
                    )
        else:
            self.body = self.content

        return True

    def validate_format(self) -> None:
        if not self.body:
            self.errors.append("No content body found")
            return

        lines = self.body.split("\n")
        non_empty_lines = [l for l in lines if l.strip()]

        if len(non_empty_lines) < 2:
            self.errors.append("Content too short (less than 2 non-empty lines)")

        if len(non_empty_lines) > 50:
            self.warnings.append("Content unusually long (>50 lines)")

        opening_blocks = len(re.findall(r"```\w*", self.body))
        closing_blocks = self.body.count("```")
        if opening_blocks != closing_blocks:
            self.errors.append(
                f"Mismatched code blocks: {opening_blocks} opening, {closing_blocks} closing"
            )

        fm_category = self.frontmatter.get("category", "")
        if fm_category and not re.match(r"^[a-z0-9-]+$", fm_category):
            self.warnings.append(
                f"Category '{fm_category}' contains non-lowercase characters"
            )

    def validate_completeness(self) -> None:
        """Check for truncation or incomplete responses."""
        for pattern in self.TRUNCATION_PATTERNS:
            if re.search(pattern, self.body, re.MULTILINE | re.IGNORECASE):
                self.errors.append(f"Possible truncation detected: matches '{pattern}'")

        if self.body.rstrip() != self.body:
            self.warnings.append("Trailing whitespace detected")

        if self.body.endswith("..."):
            self.errors.append("Content ends with ellipsis - likely truncated")

        if re.search(r"\{\{[^}]*$", self.body):
            self.errors.append("Contains unclosed template interpolation")

        code_blocks = re.findall(r"```(\w*)\n(.*?)```", self.body, re.DOTALL)
        for lang, code in code_blocks:
            if code.rstrip() != code:
                self.warnings.append("Code block has trailing whitespace")
            if len(code) < 10 and lang:
                self.warnings.append(
                    f"Code block suspiciously short for language '{lang}'"
                )

    def validate_quality(self) -> None:
        """Check for quality issues."""
        body_lower = self.body.lower()

        generic_phrases = [
            "this is a",
            "here is a",
            "in drupal, you can",
            "drupal is a",
            "one of the",
            "there are many",
        ]
        for phrase in generic_phrases:
            if body_lower.startswith(phrase):
                self.warnings.append(f"Generic opening phrase detected: '{phrase}'")

        if self.body.count("$") > 50:
            self.warnings.append(
                "Unusually high number of $ symbols - possible gibberish code"
            )

        if re.search(r"\{[\w\s,;:\'-]+\}", self.body):
            self.warnings.append("Possible placeholder text in content")

        if len(self.body) < 100:
            self.warnings.append("Content very short (<100 characters)")

        if self.body.count("```") > 6:
            self.warnings.append("Very many code blocks - content may be mostly code")

    def validate_fake_content(self) -> None:
        """Check for hallucinations or fake content."""
        for pattern in self.FAKE_PATTERNS:
            if re.search(pattern, self.content, re.IGNORECASE):
                self.errors.append(f"Suspicious fake pattern detected: '{pattern}'")

        drupal_calls = re.findall(r"\\Drupal::(\w+)\(", self.body)
        for call in drupal_calls:
            fake_methods = ["generateUUID", "createEntity", "cache", "getCache"]
            if call in fake_methods:
                self.errors.append(f"Non-existent Drupal:: method detected: {call}()")

        service_matches = re.findall(r'service\([\'"]@([\w.]+)[\'"]\)', self.body)
        for service in service_matches:
            if service not in self.KNOWN_SERVICES and not service.startswith("cache."):
                if len(service.split(".")) > 3:
                    self.warnings.append(f"Unusual service name format: {service}")

        if re.search(r"Drupal\s*<=\s*[0-9]", self.body):
            self.warnings.append("Possible incorrect version comparison")

        drush_cmds = re.findall(r"drush\s+[\w:-]+", self.body)
        for cmd in drush_cmds:
            if not any(
                k in cmd
                for k in [
                    "drush",
                    "php",
                    "core",
                    "config",
                    "state",
                    "user",
                    "cache",
                    "generate",
                    "site",
                    "watchdog",
                    "yml",
                ]
            ):
                pass

    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """
        Run all validations.

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        if not self.parse():
            return False, self.errors, self.warnings

        self.validate_format()
        self.validate_completeness()
        self.validate_quality()
        self.validate_fake_content()

        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings


def validate_tip_file(file_path: Path, verbose: bool = False) -> bool:
    """
    Validate a single tip file.

    Returns True if valid, False otherwise.
    """
    validator = TipValidator(file_path)
    is_valid, errors, warnings = validator.validate()

    if verbose or not is_valid or warnings:
        status = "✓" if is_valid else "✗"
        print(f"{status} {file_path.name}")

    if errors:
        for err in errors:
            print(f"  ERROR: {err}")

    if warnings and verbose:
        for warn in warnings:
            print(f"  WARN: {warn}")

    return is_valid


def validate_folder(
    folder_path: Path, verbose: bool = False, fix: bool = False
) -> Dict[str, Any]:
    """
    Validate all tip files in a folder.

    Returns summary statistics.
    """
    if not folder_path.is_dir():
        print(f"Not a directory: {folder_path}")
        return {"total": 0, "valid": 0, "invalid": 0, "errors": []}

    md_files = list(folder_path.rglob("*.md"))
    if not md_files:
        print(f"No .md files found in {folder_path}")
        return {"total": 0, "valid": 0, "invalid": 0, "errors": []}

    results = {"total": len(md_files), "valid": 0, "invalid": 0, "files": []}

    for md_file in md_files:
        validator = TipValidator(md_file)
        is_valid, errors, warnings = validator.validate()

        file_result = {
            "file": str(md_file.relative_to(folder_path)),
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
        }
        results["files"].append(file_result)

        if is_valid:
            results["valid"] += 1
            if verbose:
                print(f"✓ {md_file.name}")
        else:
            results["invalid"] += 1
            print(f"✗ {md_file.name}")
            for err in errors:
                print(f"    ERROR: {err}")

    return results


def validate_all_tips(verbose: bool = False) -> Dict[str, Any]:
    """
    Validate all tip files across all categories.

    Returns summary statistics.
    """
    if not TIPS_DIR.exists():
        print("Tips directory not found.")
        return {"total": 0, "valid": 0, "invalid": 0, "errors": []}

    categories = [d for d in TIPS_DIR.iterdir() if d.is_dir()]
    all_results = {"total": 0, "valid": 0, "invalid": 0, "categories": {}}

    for cat_dir in sorted(categories):
        results = validate_folder(cat_dir, verbose=verbose)
        results["category"] = cat_dir.name
        all_results["categories"][cat_dir.name] = results
        all_results["total"] += results["total"]
        all_results["valid"] += results["valid"]
        all_results["invalid"] += results["invalid"]

    return all_results


def print_validation_summary(results: Dict[str, Any]) -> None:
    """Print a formatted validation summary."""
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)
    print(f"Total files:  {results['total']}")
    print(
        f"Valid:        {results['valid']} ({100 * results['valid'] / max(results['total'], 1):.1f}%)"
    )
    print(
        f"Invalid:      {results['invalid']} ({100 * results['invalid'] / max(results['total'], 1):.1f}%)"
    )

    if "categories" in results:
        print("\nBy category:")
        for cat, data in sorted(results["categories"].items()):
            pct = 100 * data["valid"] / max(data["total"], 1)
            print(f"  {cat:25s}: {data['valid']:3d}/{data['total']:3d} ({pct:5.1f}%)")

    invalid_files = []
    for cat_data in results.get("categories", {}).values():
        for f in cat_data.get("files", []):
            if not f["valid"]:
                invalid_files.append((f["file"], f["errors"]))

    if invalid_files:
        print(f"\n{len(invalid_files)} files with errors:")
        for file_path, errors in invalid_files[:10]:
            print(f"  - {file_path}")
            for err in errors[:2]:
                print(f"      {err}")
        if len(invalid_files) > 10:
            print(f"  ... and {len(invalid_files) - 10} more")


def main():
    parser = argparse.ArgumentParser(
        description="Generate Drupal tips for the static database"
    )

    # Mutually exclusive group for main operations
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--category", "-c", type=str, help="Category number(s) or 'all'")
    group.add_argument(
        "--list-categories", action="store_true", help="List all categories"
    )
    group.add_argument(
        "--check-batch", type=str, metavar="BATCH_ID", help="Check batch status"
    )
    group.add_argument(
        "--random-tip",
        action="store_true",
        help="Get a random existing tip (fast, no API call)",
    )
    group.add_argument(
        "--list-existing",
        action="store_true",
        help="List categories with existing tips",
    )
    group.add_argument(
        "--validate",
        action="store_true",
        help="Validate tip files (use with --validate-file, --validate-category, or --validate-all)",
    )
    group.add_argument(
        "--fetch-data",
        action="store_true",
        help="Fetch and cache remote data for categories with URLs (run before generating)",
    )
    group.add_argument(
        "--fetch-category",
        type=int,
        metavar="N",
        help="Fetch data for a specific category only",
    )
    parser.add_argument(
        "--validate-file",
        type=str,
        metavar="FILE",
        help="Validate a specific tip file",
    )
    parser.add_argument(
        "--validate-category",
        type=str,
        metavar="CATEGORY",
        help="Validate all tips in a category folder",
    )
    parser.add_argument(
        "--validate-all",
        action="store_true",
        help="Validate all tip files across all categories",
    )
    parser.add_argument(
        "--tip-category",
        type=str,
        default=None,
        help="Filter random tip by category name (use with --random-tip)",
    )

    parser.add_argument(
        "--count",
        "-n",
        type=int,
        default=5,
        help="Number of tips per category (default: 5)",
    )
    parser.add_argument(
        "--provider",
        "-p",
        type=str,
        choices=["anthropic", "openai", "openrouter"],
        help="LLM provider to use",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help=f"Model to use (defaults from .env or: anthropic={DEFAULT_MODELS['anthropic']}, openai={DEFAULT_MODELS['openai']}, openrouter={DEFAULT_MODELS['openrouter']})",
    )
    parser.add_argument(
        "--api-key", "-k", type=str, default=None, help="API key (or set in .env)"
    )
    parser.add_argument(
        "--no-wait", action="store_true", help="Don't wait for batch completion"
    )
    parser.add_argument(
        "--save-results", action="store_true", help="Save results when checking batch"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without calling API",
    )

    args = parser.parse_args()

    if args.list_categories:
        list_categories()
        return

    if args.list_existing:
        list_existing_categories()
        return

    if args.random_tip:
        print_random_tip(args.tip_category)
        return

    if args.fetch_data:
        if not HAS_URL_CACHE:
            print("Error: url_cache module not available")
            return
        print("Fetching remote data for all categories with URLs...")
        results = fetch_all_category_data(force=True)
        total = sum(len(paths) for paths in results.values())
        print(f"\nDone! Cached {total} files for {len(results)} categories.")
        return

    if args.fetch_category:
        if not HAS_URL_CACHE:
            print("Error: url_cache module not available")
            return
        if args.fetch_category not in CATEGORIES:
            print(f"Error: Category {args.fetch_category} not found")
            return
        cat_info = CATEGORIES[args.fetch_category]
        print(f"Fetching data for category {args.fetch_category}: {cat_info['name']}")
        cached = fetch_category_urls(args.fetch_category, cat_info, force=True)
        print(f"\nCached {len(cached)} files")
        return

    if (
        args.validate
        or args.validate_file
        or args.validate_category
        or args.validate_all
    ):
        if args.validate_file:
            file_path = Path(args.validate_file)
            if not file_path.exists():
                print(f"File not found: {file_path}")
                return
            validate_tip_file(file_path, verbose=True)
            return

        if args.validate_category:
            cat_path = TIPS_DIR / args.validate_category
            if not cat_path.exists():
                print(f"Category not found: {args.validate_category}")
                list_existing_categories()
                return
            results = validate_folder(cat_path, verbose=True)
            print_validation_summary(results)
            return

        if args.validate_all:
            results = validate_all_tips(verbose=True)
            print_validation_summary(results)
            return

        print(
            "Error: --validate requires --validate-file, --validate-category, or --validate-all"
        )
        return

    if args.check_batch:
        if not args.provider:
            print("Error: --provider is required for --check-batch")
            return

        # Get API key
        if args.api_key:
            api_key = args.api_key
        else:
            env_key = f"{args.provider.upper()}_API_KEY"
            api_key = get_env(env_key)
            if not api_key:
                print(
                    f"Error: No API key. Set {env_key} (or TIPGEN_{env_key}) in .env or use --api-key"
                )
                return

        check_batch_status(args.check_batch, args.provider, api_key, args.save_results)
        return

    # Parse categories
    if args.category.lower() == "all":
        categories = list(CATEGORIES.keys())
    else:
        try:
            categories = [int(c.strip()) for c in args.category.split(",")]
        except ValueError:
            print("Error: Invalid category format. Use numbers or 'all'")
            return

    if not args.provider:
        print("Error: --provider is required for generation")
        return

    # Get API key
    if args.api_key:
        api_key = args.api_key
    else:
        env_key = f"{args.provider.upper()}_API_KEY"
        api_key = get_env(env_key)
        if not api_key and not args.dry_run:
            print(
                f"Error: No API key. Set {env_key} (or TIPGEN_{env_key}) in .env or use --api-key"
            )
            return

    use_sync = args.provider == "openrouter"

    if args.dry_run:
        print(
            f"DRY RUN - Would generate {args.count} tips for categories: {categories}"
        )
        print(f"Provider: {args.provider}")
        print(f"Model: {args.model or get_default_model(args.provider)}")
        print(f"Mode: {'sync' if use_sync else 'batch'}")
        return

    if use_sync:
        generated = generate_sync(
            categories, args.count, args.provider, api_key, args.model
        )
    else:
        generated = generate_batch(
            categories, args.count, args.provider, api_key, args.model, not args.no_wait
        )

    print(f"\nTotal tips generated: {generated}")


if __name__ == "__main__":
    main()
