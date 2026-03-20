#!/usr/bin/env python3
"""
Drupal Tip Generator - Generate static MD files for the drupal-tip skill.

Usage:
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
import time
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

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
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    os.environ[key] = value

# Load .env on import
load_env_file()

def get_env(key: str, default: str = None) -> Optional[str]:
    """Get env var, checking TIPGEN_ prefix first, then global."""
    return os.environ.get(f'TIPGEN_{key}') or os.environ.get(key, default)

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

def get_prompt_for_category(cat_id: int, cat_info: dict) -> str:
    """Generate a prompt for a specific category using the template from config."""
    template = CONFIG.get("prompt_template", "")

    return template.format(
        cat_id=cat_id,
        cat_desc=cat_info['desc'],
        cat_name=cat_info['name']
    )

def generate_file_id() -> str:
    """Generate an 8-character lowercase random ID."""
    return uuid.uuid4().hex[:8]

def save_tip(cat_info: dict, content: str) -> Optional[Path]:
    """Save a tip to the appropriate file."""
    category_dir = TIPS_DIR / cat_info['name']
    category_dir.mkdir(parents=True, exist_ok=True)

    file_id = generate_file_id()
    file_path = category_dir / f"{file_id}.md"
    
    # Add metadata if not present
    if not content.startswith('---'):
        content = f"""---
category: {cat_info['name']}
generated: {datetime.now().isoformat()}
---

{content}"""
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    return file_path

# ============ BATCH API FUNCTIONS ============

def anthropic_batch_create(requests: List[dict], api_key: str) -> str:
    """Create an Anthropic batch and return the batch ID."""
    client = anthropic.Anthropic(api_key=api_key)

    # Build message batch requests
    batch_requests = []
    for req in requests:
        batch_requests.append({
            "custom_id": req.get("custom_id", str(uuid.uuid4())),
            "params": {
                "model": req.get("model", get_default_model("anthropic")),
                "max_tokens": 2048,
                "messages": [
                    {"role": "user", "content": req["prompt"]}
                ]
            }
        })

    batch = client.messages.batches.create(requests=batch_requests)
    return batch.id

def anthropic_batch_check(batch_id: str, api_key: str) -> dict:
    """Check Anthropic batch status and return results if complete."""
    client = anthropic.Anthropic(api_key=api_key)
    batch = client.messages.batches.retrieve(batch_id)
    
    result = {
        "status": batch.processing_status,
        "complete": batch.processing_status == "ended",
        "results": []
    }
    
    if result["complete"]:
        # Get results
        for res in client.messages.batches.results(batch_id):
            if res.result.type == "succeeded":
                result["results"].append({
                    "custom_id": res.custom_id,
                    "content": res.result.message.content[0].text
                })
    
    return result

def openai_batch_create(requests: List[dict], api_key: str, model: str = None) -> str:
    """Create an OpenAI batch and return the batch ID."""
    client = OpenAI(api_key=api_key)
    model = model or get_default_model("openai")
    
    # Create JSONL file content
    jsonl_content = ""
    for req in requests:
        jsonl_content += json.dumps({
            "custom_id": req.get("custom_id", str(uuid.uuid4())),
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": model,
                "max_completion_tokens": 2048,
                "messages": [
                    {"role": "user", "content": req["prompt"]}
                ]
            }
        }) + "\n"
    
    # Upload file
    batch_file = client.files.create(
        file=jsonl_content.encode('utf-8'),
        purpose="batch"
    )
    
    # Create batch
    batch = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h"
    )
    
    return batch.id

def openai_batch_check(batch_id: str, api_key: str) -> dict:
    """Check OpenAI batch status and return results if complete."""
    client = OpenAI(api_key=api_key)
    batch = client.batches.retrieve(batch_id)
    
    result = {
        "status": batch.status,
        "complete": batch.status in ["completed", "failed", "expired"],
        "results": []
    }
    
    if batch.status == "completed" and batch.output_file_id:
        # Get results
        file_content = client.files.content(batch.output_file_id)
        for line in file_content.text.strip().split('\n'):
            data = json.loads(line)
            if data.get("response", {}).get("status_code") == 200:
                body = data["response"]["body"]
                result["results"].append({
                    "custom_id": data["custom_id"],
                    "content": body["choices"][0]["message"]["content"]
                })
    
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
        }
    )
    batch = client.batches.retrieve(batch_id)

    result = {
        "status": batch.status,
        "complete": batch.status in ["completed", "failed", "expired"],
        "results": []
    }

    if batch.status == "completed" and batch.output_file_id:
        # Get results
        file_content = client.files.content(batch.output_file_id)
        for line in file_content.text.strip().split('\n'):
            data = json.loads(line)
            if data.get("response", {}).get("status_code") == 200:
                body = data["response"]["body"]
                result["results"].append({
                    "custom_id": data["custom_id"],
                    "content": body["choices"][0]["message"]["content"]
                })

    return result

def openrouter_batch_create(requests: List[dict], api_key: str, model: str = None) -> str:
    """Create an OpenRouter batch - uses OpenAI-compatible API with OpenRouter base URL."""
    model = model or get_default_model("openrouter")
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/drupaltools/drupal-tip-generator",
            "X-OpenRouter-Title": "Drupal Tip Generator",
            "X-OpenRouter-Categories": "cli-agent",
        }
    )

    # Create JSONL file content
    jsonl_content = ""
    for req in requests:
        jsonl_content += json.dumps({
            "custom_id": req.get("custom_id", str(uuid.uuid4())),
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": model,
                "max_completion_tokens": 2048,
                "messages": [
                    {"role": "user", "content": req["prompt"]}
                ]
            }
        }) + "\n"

    # Upload file
    batch_file = client.files.create(
        file=jsonl_content.encode('utf-8'),
        purpose="batch"
    )

    # Create batch
    batch = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h"
    )

    return batch.id

# ============ SYNC API FUNCTIONS ============

def call_anthropic_sync(prompt: str, api_key: str, model: str = None) -> dict:
    """Call Anthropic API synchronously."""
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model or get_default_model("anthropic"),
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )
    return {
        "content": message.content[0].text,
        "finish_reason": message.stop_reason  # "end_turn" or "max_tokens"
    }

def call_openai_sync(prompt: str, api_key: str, model: str = None) -> dict:
    """Call OpenAI API synchronously."""
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model or get_default_model("openai"),
        max_completion_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )
    return {
        "content": response.choices[0].message.content,
        "finish_reason": response.choices[0].finish_reason  # "stop" or "length"
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
        }
    )
    response = client.chat.completions.create(
        model=model or get_default_model("openrouter"),
        max_completion_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )
    return {
        "content": response.choices[0].message.content,
        "finish_reason": response.choices[0].finish_reason  # "stop" or "length"
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

    with open(ERROR_LOG_FILE, 'w') as f:
        json.dump(errors, f, indent=2)

def generate_sync(categories: List[int], count: int, provider: str, api_key: str, model: Optional[str]) -> int:
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

            print(f"  Generating tip {i+1}/{count}...", end=" ", flush=True)

            try:
                if provider == "anthropic":
                    tip_data = call_anthropic_sync(prompt, api_key, model or get_default_model("anthropic"))
                elif provider == "openai":
                    tip_data = call_openai_sync(prompt, api_key, model or get_default_model("openai"))
                elif provider == "openrouter":
                    tip_data = call_openrouter_sync(prompt, api_key, model or get_default_model("openrouter"))
                else:
                    raise ValueError(f"Unknown provider: {provider}")

                # Check for truncation
                finish_reason = tip_data.get("finish_reason", "unknown")
                if finish_reason in ("length", "max_tokens"):
                    print(f"TRUNCATED ({finish_reason})")
                    truncated += 1
                    log_error({
                        "timestamp": datetime.now().isoformat(),
                        "category_id": cat_id,
                        "category_name": cat_info.get('name'),
                        "tip_number": i + 1,
                        "provider": provider,
                        "model": model or get_default_model(provider),
                        "error": f"Response truncated (finish_reason: {finish_reason})",
                        "content": tip_data.get("content", "")[:500]  # First 500 chars for debugging
                    })
                    continue

                file_path = save_tip(cat_info, tip_data["content"])
                print(f"Saved to {file_path.relative_to(SCRIPT_DIR)}")
                generated += 1

            except Exception as e:
                print(f"Error: {e}")
                log_error({
                    "timestamp": datetime.now().isoformat(),
                    "category_id": cat_id,
                    "category_name": cat_info.get('name'),
                    "tip_number": i + 1,
                    "provider": provider,
                    "model": model or get_default_model(provider),
                    "error": str(e)
                })

    if truncated > 0:
        print(f"\nWarning: {truncated} tips were truncated and not saved (see errors.json)")

    return generated

def generate_batch(categories: List[int], count: int, provider: str, api_key: str, model: Optional[str], wait: bool = True) -> int:
    """Generate tips using batch API (50% cheaper)."""
    requests = []
    
    for cat_id in categories:
        if cat_id not in CATEGORIES:
            print(f"Warning: Category {cat_id} not found, skipping")
            continue
        
        cat_info = CATEGORIES[cat_id]
        
        for i in range(count):
            prompt = get_prompt_for_category(cat_id, cat_info)
            requests.append({
                "custom_id": f"{cat_info['name']}_{i+1}",
                "prompt": prompt,
                "model": model
            })
    
    if not requests:
        print("No requests to process")
        return 0
    
    print(f"Creating batch with {len(requests)} requests...")
    
    try:
        if provider == "anthropic":
            batch_id = anthropic_batch_create(requests, api_key)
        elif provider == "openai":
            batch_id = openai_batch_create(requests, api_key, model or get_default_model("openai"))
        elif provider == "openrouter":
            batch_id = openrouter_batch_create(requests, api_key, model or get_default_model("openrouter"))
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        print(f"Batch created: {batch_id}")
        print(f"Check status with: python tip_generator.py --check-batch {batch_id} -p {provider}")
        
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
                print(f"\nBatch complete! Processing {len(result['results'])} results...")
                
                generated = 0
                for res in result["results"]:
                    custom_id = res["custom_id"]
                    # Extract category name from custom_id
                    cat_name = custom_id.rsplit('_', 1)[0]
                    cat_info = next((c for c in CATEGORIES.values() if c["name"] == cat_name), None)
                    
                    if cat_info:
                        file_path = save_tip(cat_info, res["content"])
                        print(f"  Saved: {file_path.relative_to(SCRIPT_DIR)}")
                        generated += 1
                
                return generated
            
            time.sleep(10)
            
    except Exception as e:
        print(f"Batch error: {e}")
        return 0

def check_batch_status(batch_id: str, provider: str, api_key: str, save: bool = False) -> None:
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
                cat_name = custom_id.rsplit('_', 1)[0]
                cat_info = next((c for c in CATEGORIES.values() if c["name"] == cat_name), None)
                
                if cat_info:
                    file_path = save_tip(cat_info, res["content"])
                    print(f"  Saved: {file_path.relative_to(SCRIPT_DIR)}")
        
    except Exception as e:
        print(f"Error: {e}")

def list_categories():
    """List all available categories."""
    print("Available categories:\n")
    for cat_id, info in CATEGORIES.items():
        live = " [LIVE]" if info["live_fetch"] else ""
        print(f"  {cat_id:2d}. {info['desc']}{live}")
    print(f"\nTotal: {len(CATEGORIES)} categories")
    print("\nUse 'all' as category to generate for all categories")

def main():
    parser = argparse.ArgumentParser(description="Generate Drupal tips for the static database")
    
    # Mutually exclusive group for main operations
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--category", "-c", type=str, help="Category number(s) or 'all'")
    group.add_argument("--list-categories", action="store_true", help="List all categories")
    group.add_argument("--check-batch", type=str, metavar="BATCH_ID", help="Check batch status")
    
    parser.add_argument("--count", "-n", type=int, default=5, help="Number of tips per category (default: 5)")
    parser.add_argument("--provider", "-p", type=str, choices=["anthropic", "openai", "openrouter"], 
                        help="LLM provider to use")
    parser.add_argument("--model", "-m", type=str, default=None, 
                        help=f"Model to use (defaults from .env or: anthropic={DEFAULT_MODELS['anthropic']}, openai={DEFAULT_MODELS['openai']}, openrouter={DEFAULT_MODELS['openrouter']})")
    parser.add_argument("--api-key", "-k", type=str, default=None, help="API key (or set in .env)")
    parser.add_argument("--sync", action="store_true", help="Use synchronous API instead of batch")
    parser.add_argument("--no-wait", action="store_true", help="Don't wait for batch completion")
    parser.add_argument("--save-results", action="store_true", help="Save results when checking batch")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without calling API")
    
    args = parser.parse_args()
    
    if args.list_categories:
        list_categories()
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
                print(f"Error: No API key. Set {env_key} (or TIPGEN_{env_key}) in .env or use --api-key")
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
            print(f"Error: No API key. Set {env_key} (or TIPGEN_{env_key}) in .env or use --api-key")
            return
    
    # Auto-enable sync mode for providers that don't support batch API
    if args.provider in ("openrouter", "anthropic") and not args.sync:
        args.sync = True
        print(f"Note: Auto-enabled --sync mode (batch API not supported for {args.provider})")

    if args.dry_run:
        print(f"DRY RUN - Would generate {args.count} tips for categories: {categories}")
        print(f"Provider: {args.provider}")
        print(f"Model: {args.model or get_default_model(args.provider)}")
        print(f"Mode: {'sync' if args.sync else 'batch'}")
        return
    
    # Generate
    if args.sync:
        generated = generate_sync(categories, args.count, args.provider, api_key, args.model)
    else:
        generated = generate_batch(categories, args.count, args.provider, api_key, args.model, not args.no_wait)
    
    print(f"\nTotal tips generated: {generated}")

if __name__ == "__main__":
    main()
