#!/usr/bin/env python3
"""
Drupal Tip Viewer - Web UI to browse and display tips.

Usage:
    python tip_viewer.py                    # Start web server (default: http://localhost:5000)
    python tip_viewer.py --port 8080        # Custom port
    python tip_viewer.py --tips-dir ./tips  # Custom tips directory
"""

import argparse
import random
import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

from flask import Flask, render_template, jsonify, request

SCRIPT_DIR = Path(__file__).parent


def get_tips_dir(cli_path: Optional[str] = None) -> Path:
    """Get tips directory with priority: CLI > env var > default."""
    # 1. CLI argument (highest priority)
    if cli_path:
        return Path(cli_path).expanduser().resolve()

    # 2. Environment variable
    env_path = os.environ.get("TIPGEN_TIPS_DIR")
    if env_path:
        return Path(env_path).expanduser().resolve()

    # 3. Default (lowest priority)
    return SCRIPT_DIR / "tips"


# Default tips directory (can be overridden via CLI/env)
TIPS_DIR = get_tips_dir()

app = Flask(
    __name__, static_folder=str(SCRIPT_DIR / "static"), static_url_path="/static"
)


def parse_tip_file(file_path: Path) -> Dict[str, Any]:
    """Parse a tip .md file and extract metadata and content."""
    with open(file_path) as f:
        content = f.read()

    frontmatter = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            body = parts[2].strip()

            current_key = None
            current_value = ""
            for line in fm_text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if ":" in line:
                    if current_key:
                        frontmatter[current_key] = current_value.strip()
                    parts_line = line.split(":", 1)
                    current_key = parts_line[0].strip()
                    current_value = parts_line[1].strip() if len(parts_line) > 1 else ""
            if current_key:
                frontmatter[current_key] = current_value.strip()

    return {
        "file": file_path.name,
        "uuid": file_path.stem,
        "path": str(file_path),
        "category": frontmatter.get("category", file_path.parent.name),
        "title": frontmatter.get("title", ""),
        "generated": frontmatter.get("generated", ""),
        "content": body.strip(),
    }


def get_categories() -> List[Dict[str, Any]]:
    """Get all categories with tip counts."""
    if not TIPS_DIR.exists():
        return []

    categories = []
    for cat_dir in sorted(TIPS_DIR.iterdir()):
        if cat_dir.is_dir():
            tip_files = list(cat_dir.glob("*.md"))
            categories.append(
                {
                    "name": cat_dir.name,
                    "count": len(tip_files),
                }
            )
    return categories


def get_tips(category: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Get tips, optionally filtered by category."""
    if not TIPS_DIR.exists():
        return []

    if category:
        cat_dir = TIPS_DIR / category
        if not cat_dir.exists():
            return []
        tip_files = list(cat_dir.glob("*.md"))[:limit]
    else:
        tip_files = list(TIPS_DIR.rglob("*.md"))[:limit]

    tips = []
    for f in tip_files:
        try:
            tips.append(parse_tip_file(f))
        except Exception:
            continue

    return tips


def get_random_tip(category: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get a random tip, optionally filtered by category."""
    if not TIPS_DIR.exists():
        return None

    if category:
        cat_dir = TIPS_DIR / category
        if not cat_dir.exists():
            return None
        tip_files = list(cat_dir.glob("*.md"))
    else:
        tip_files = list(TIPS_DIR.rglob("*.md"))

    if not tip_files:
        return None

    tip_file = random.choice(tip_files)
    return parse_tip_file(tip_file)


@app.route("/")
def index():
    categories = get_categories()
    total_tips = sum(c["count"] for c in categories)
    return render_template(
        "index.html",
        categories=categories,
        total_tips=total_tips,
        tips_dir=str(TIPS_DIR),
    )


@app.route("/about")
def about():
    categories = get_categories()
    total_tips = sum(c["count"] for c in categories)
    return render_template("about.html", categories=categories, total_tips=total_tips)


@app.route("/api/tips")
def api_tips():
    category = request.args.get("category")
    limit = request.args.get("limit", 100, type=int)
    tips = get_tips(category=category, limit=limit)
    return jsonify({"tips": tips, "count": len(tips)})


@app.route("/api/random")
def api_random():
    category = request.args.get("category")
    tip = get_random_tip(category=category)
    if tip:
        return jsonify(tip)
    return jsonify({"error": "No tips found"}), 404


@app.route("/api/categories")
def api_categories():
    return jsonify({"categories": get_categories()})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Drupal Tip Viewer Web UI")
    parser.add_argument("--port", type=int, default=5000, help="Port to run on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--tips-dir", type=str, default=None, help="Tips directory (or set TIPGEN_TIPS_DIR env var)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    # Update TIPS_DIR based on CLI argument (overrides default/env)
    global TIPS_DIR
    TIPS_DIR = get_tips_dir(args.tips_dir)

    app.run(host=args.host, port=args.port, debug=args.debug)
