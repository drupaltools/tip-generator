#!/usr/bin/env python3
"""Fetch and cache remote content for tip generation."""

import re
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

import requests
import html2text

from tip_generator import DATA_DIR

CACHE_DIR = DATA_DIR / "cache" / "url_cache"
USER_AGENT = (
    "DrupalTipGenerator/1.0 (https://github.com/drupaltools/drupaltools-tip-generator)"
)
FETCH_TIMEOUT = 30


def ensure_cache_dir() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def extract_urls(text: str) -> List[str]:
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return list(set(re.findall(url_pattern, text)))


def is_homepage_url(url: str) -> bool:
    from urllib.parse import urlparse

    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    return path == "" or path == parsed.netloc


def get_url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def fetch_wikipedia(url: str) -> tuple[str, str]:
    match = re.search(r"wikipedia\.org/wiki/([^/?#]+)", url)
    if not match:
        return None, None

    title = match.group(1).replace("_", " ")
    api_url = f"https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": title,
        "prop": "extracts",
        "exintro": False,
        "explaintext": True,
        "format": "json",
    }
    response = requests.get(
        api_url,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=FETCH_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()

    pages = data.get("query", {}).get("pages", {})
    for page_data in pages.values():
        if "extract" in page_data:
            return page_data["extract"], page_data.get("title", title)

    return None, None


def fetch_html(url: str) -> tuple[str, str, list, list]:
    if "wikipedia.org" in url.lower():
        extract, title = fetch_wikipedia(url)
        if extract:
            return extract, title, [], []

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=FETCH_TIMEOUT)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")
    text_content = response.text

    if "text/plain" in content_type or url.endswith(".md") or url.endswith(".txt"):
        title_match = re.search(
            r"<title[^>]*>([^<]+)</title>", text_content, re.IGNORECASE
        )
        title = title_match.group(1).strip() if title_match else ""
        return text_content, title, [], []

    html_content = text_content
    title_match = re.search(r"<title[^>]*>([^<]+)</title>", html_content, re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else ""

    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.body_width = 0
    h.unicode_snob = True

    html_content = re.sub(
        r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL | re.IGNORECASE
    )
    html_content = re.sub(
        r"<style[^>]*>.*?</style>", "", html_content, flags=re.DOTALL | re.IGNORECASE
    )

    markdown_content = h.handle(html_content)
    markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)
    markdown_content = clean_markdown(markdown_content)

    sub_links, pagination_links = _extract_sub_links(html_content, url, max_links=20)

    return markdown_content.strip(), title, sub_links, pagination_links


def _extract_pagination_links(
    html_content: str, base_url: str, max_pages: int = 5
) -> List[str]:
    from urllib.parse import urljoin, urlparse, parse_qs, urlencode

    pagination_patterns = [
        r"[?&](page|p|offset)=\d+",
        r"/(?:page|p|offset)/\d+",
    ]

    try:
        base_parsed = urlparse(base_url)
    except Exception:
        return []

    link_pattern = re.compile(r'<a\s+[^>]*href=["\']([^"\']+)["\']', re.IGNORECASE)
    pagination_links = []
    seen_pages = set()
    seen_pages.add(base_url)

    for match in link_pattern.finditer(html_content):
        href = match.group(1).strip()
        if (
            not href
            or href.startswith("#")
            or href.startswith("mailto:")
            or href.startswith("tel:")
        ):
            continue

        full_url = urljoin(base_url, href)
        url_parsed = urlparse(full_url)

        if not url_parsed.netloc or not url_parsed.netloc.startswith(
            base_parsed.netloc
        ):
            continue

        is_pagination = False
        for pattern in pagination_patterns:
            if re.search(pattern, full_url, re.IGNORECASE):
                is_pagination = True
                break

        if is_pagination and full_url not in seen_pages:
            pagination_links.append(full_url)
            seen_pages.add(full_url)

    return pagination_links[:max_pages]


def _extract_sub_links(
    html_content: str, base_url: str, max_links: int = 20, max_pages: int = 5
) -> tuple:
    from urllib.parse import urljoin, urlparse, urlunparse

    try:
        base_parsed = urlparse(base_url)
    except Exception:
        return [], []

    base_path = base_parsed.path.rstrip("/")
    if not base_path:
        base_path = "/"

    link_pattern = re.compile(r'<a\s+[^>]*href=["\']([^"\']+)["\']', re.IGNORECASE)
    pagination_patterns = [
        r"[?&](page|p|offset)=\d+",
        r"/(?:page|p|offset)/\d+",
    ]

    found = []
    seen = set()
    pagination_links = []
    seen_pagination = set()

    for match in link_pattern.finditer(html_content):
        href = match.group(1).strip()
        if (
            not href
            or href.startswith("#")
            or href.startswith("mailto:")
            or href.startswith("tel:")
        ):
            continue

        full_url = urljoin(base_url, href)
        url_parsed = urlparse(full_url)

        if not url_parsed.netloc or not url_parsed.netloc.startswith(
            base_parsed.netloc
        ):
            continue

        is_pagination = False
        for pattern in pagination_patterns:
            if re.search(pattern, full_url, re.IGNORECASE):
                is_pagination = True
                break

        if is_pagination:
            if full_url not in seen_pagination and len(pagination_links) < max_pages:
                pagination_links.append(full_url)
                seen_pagination.add(full_url)
            continue

        url_path = url_parsed.path.rstrip("/")
        if not url_path:
            url_path = "/"

        if url_path == base_path:
            continue

        if url_parsed.query:
            continue

        url_segments = url_path.strip("/").split("/")
        base_segments = base_path.strip("/").split("/")

        if len(url_segments) <= len(base_segments):
            continue

        if full_url in seen:
            continue
        seen.add(full_url)
        found.append(full_url)

        if len(found) >= max_links:
            break

    return found, pagination_links


def clean_markdown(content: str) -> str:
    content = re.sub(r"\\-", "-", content)
    content = re.sub(r"\\\*", "*", content)
    content = re.sub(r"\\`", "`", content)
    content = re.sub(r"\\#", "#", content)
    content = re.sub(r"\\_", "_", content)

    lines = content.split("\n")
    cleaned = []
    prev_empty = False

    for line in lines:
        line = line.rstrip()
        stripped = line.strip()

        if re.match(r"^[-*_]{3,}$", stripped):
            continue
        if not stripped:
            if not prev_empty:
                cleaned.append("")
            prev_empty = True
            continue

        if len(stripped) > 300:
            parts = re.split(r"\\\+|\s+\\\s+|\s{2,}", stripped)
            for part in parts:
                part = part.strip()
                if part and len(part) > 20:
                    cleaned.append(part)
            prev_empty = False
            continue

        cleaned.append(line)
        prev_empty = False

    return "\n".join(cleaned)


def fetch_json(url: str) -> tuple[Any, str]:
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=FETCH_TIMEOUT)
    response.raise_for_status()
    return response.json(), url


def fetch_url(url: str) -> Dict[str, Any]:
    result = {
        "url": url,
        "cached_at": datetime.now().isoformat(),
    }

    if url.endswith(".json"):
        content_type = "json"
    else:
        content_type = "html"

    headers = {"User-Agent": USER_AGENT}
    head_response = requests.head(
        url, headers=headers, timeout=10, allow_redirects=True
    )
    content_type_header = head_response.headers.get("Content-Type", "")

    if "application/json" in content_type_header:
        content_type = "json"

    try:
        if content_type == "json":
            data, source = fetch_json(url)
            result["type"] = "json"
            result["content"] = data
            result["source_url"] = source
        else:
            markdown, title, sub_links, pagination_links = fetch_html(url)
            result["type"] = "markdown"
            result["content"] = markdown
            result["title"] = title
            result["source_url"] = url
            result["sub_links"] = sub_links
            result["pagination_links"] = pagination_links

    except requests.RequestException as e:
        result["error"] = str(e)
        result["type"] = "error"

    return result


def _slugify(text: str) -> str:
    import re

    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"^-|-$", "", text)
    return text


def cache_content(url: str, data: Dict[str, Any], category_name: str = "") -> Path:
    ensure_cache_dir()

    url_hash = get_url_hash(url)
    content_type = data.get("type", "unknown")
    extension = "json" if content_type == "json" else "md"

    if category_name:
        slug = _slugify(category_name)
        counter = 1
        base_name = f"{slug}-{counter}"
        while (CACHE_DIR / f"{base_name}.{extension}").exists():
            counter += 1
            base_name = f"{slug}-{counter}"
        cache_file = CACHE_DIR / f"{base_name}.{extension}"
    else:
        cache_file = CACHE_DIR / f"{url_hash}.{extension}"

    cache_entry = {
        "url": url,
        "cached_at": data.get("cached_at"),
        "type": content_type,
        "title": data.get("title"),
        "source_url": data.get("source_url"),
        "sub_links": data.get("sub_links", []),
        "pagination_links": data.get("pagination_links", []),
    }

    if content_type == "json":
        cache_entry["data"] = data.get("content")
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_entry, f, indent=2, ensure_ascii=False)
    else:
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write(f"url: {url}\n")
            f.write(f"cached_at: {data.get('cached_at')}\n")
            f.write(f"title: {data.get('title', '')}\n")
            f.write(f"source_url: {data.get('source_url', '')}\n")
            f.write(f"sub_links: {json.dumps(data.get('sub_links', []))}\n")
            f.write(
                f"pagination_links: {json.dumps(data.get('pagination_links', []))}\n"
            )
            f.write("---\n\n")
            f.write(data.get("content", ""))

    return cache_file


def get_cached_content(url: str) -> Optional[Dict[str, Any]]:
    url_hash = get_url_hash(url)

    for ext in ["md", "json"]:
        cache_file = CACHE_DIR / f"{url_hash}.{ext}"
        if cache_file.exists():
            if ext == "json":
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                with open(cache_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            fm_text = parts[1]
                            body = parts[2].strip()
                            fm_data = {}
                            for line in fm_text.strip().split("\n"):
                                if ":" in line:
                                    key, val = line.split(":", 1)
                                    fm_data[key.strip()] = val.strip()
                            sub_links_raw = fm_data.get("sub_links", "[]")
                            pagination_links_raw = fm_data.get("pagination_links", "[]")
                            try:
                                sub_links = json.loads(sub_links_raw)
                            except json.JSONDecodeError:
                                sub_links = []
                            try:
                                pagination_links = json.loads(pagination_links_raw)
                            except json.JSONDecodeError:
                                pagination_links = []
                            return {
                                "type": "markdown",
                                "content": body,
                                "title": fm_data.get("title", ""),
                                "url": fm_data.get("url", url),
                                "cached_at": fm_data.get("cached_at", ""),
                                "sub_links": sub_links,
                                "pagination_links": pagination_links,
                            }
                    return {"type": "markdown", "content": content}

    return None


def is_cache_valid(cache_entry: Dict[str, Any], max_age_hours: int = 24) -> bool:
    cached_at = cache_entry.get("cached_at", "")
    if not cached_at:
        return False

    try:
        cached_time = datetime.fromisoformat(cached_at)
        age = datetime.now() - cached_time
        return age.total_seconds() < (max_age_hours * 3600)
    except (ValueError, TypeError):
        return False


def fetch_category_urls(
    category_id: int, category_info: Dict[str, Any], force: bool = False
) -> List[Path]:
    description = category_info.get("desc", "")

    # Get URLs from both 'urls' field and description text
    urls = list(category_info.get("urls", [])) if "urls" in category_info else []
    urls.extend(extract_urls(description))
    urls = list(set(urls))  # Deduplicate

    if not urls:
        return []

    cached_files = []
    for url in urls:
        if is_homepage_url(url):
            print(f"  [skip] homepage URL: {url}")
            continue

        cached = get_cached_content(url)

        if cached and not force and is_cache_valid(cached):
            print(f"  [cached] {url}")
            url_hash = get_url_hash(url)
            ext = "json" if cached.get("type") == "json" else "md"
            cached_files.append(CACHE_DIR / f"{url_hash}.{ext}")
        else:
            print(f"  [fetching] {url}")
            try:
                data = fetch_url(url)
                if data.get("type") != "error":
                    cache_file = cache_content(url, data)
                    cached_files.append(cache_file)
                    print(f"    -> saved to {cache_file.name}")
                else:
                    print(f"    -> ERROR: {data.get('error')}")
            except Exception as e:
                print(f"    -> ERROR: {e}")

    return cached_files


def fetch_all_category_data(force: bool = False) -> Dict[int, List[Path]]:
    from tip_generator import CATEGORIES

    results = {}
    for cat_id, cat_info in CATEGORIES.items():
        # Get URLs from both 'urls' field and description text
        urls = list(cat_info.get("urls", [])) if "urls" in cat_info else []
        urls.extend(extract_urls(cat_info.get("desc", "")))
        urls = list(set(urls))
        if urls:
            print(f"\nCategory {cat_id}: {cat_info['name']}")
            cached = fetch_category_urls(cat_id, cat_info, force=force)
            results[cat_id] = cached

    return results


def _format_cached_content(url: str, cached: Dict[str, Any]) -> str:
    if cached.get("type") == "json":
        data = cached.get("data", {})
        if isinstance(data, list) and len(data) > 0:
            sample = data[:10]
            return f"Data from {url}:\n```json\n{json.dumps(sample, indent=2)}\n```"
        elif isinstance(data, dict):
            return f"Data from {url}:\n```json\n{json.dumps(data, indent=2)}\n```"
    else:
        title = cached.get("title", "Untitled")
        content = cached.get("content", "")
        if len(content) > 10000:
            content = content[:10000] + "\n\n[... content truncated ...]"
        return f"Reference from {url} ({title}):\n\n{content}"
    return ""


def build_context_for_category(category_id: int, category_info: Dict[str, Any]) -> str:
    import random

    description = category_info.get("desc", "")

    urls = list(category_info.get("urls", [])) if "urls" in category_info else []
    urls.extend(extract_urls(description))
    urls = list(set(urls))

    if not urls:
        return ""

    if len(urls) > 1:
        urls = [random.choice(urls)]

    sub_paths = category_info.get("sub_paths", [])

    context_parts = []

    for url in urls:
        cached = get_cached_content(url)
        if cached and is_cache_valid(cached):
            page_content = cached
        else:
            print(f"  [fetching] {url}")
            try:
                data = fetch_url(url)
                if "error" not in data:
                    cache_content(url, data)
                    page_content = data
                else:
                    print(f"  [error] Failed to fetch {url}: {data.get('error')}")
                    continue
            except Exception as e:
                print(f"  [error] Failed to fetch {url}: {e}")
                continue

        formatted = _format_cached_content(url, page_content)
        if formatted:
            context_parts.append(formatted)

        sub_links = page_content.get("sub_links", [])
        if sub_paths:
            sub_links = [
                u for u in sub_links if any(u.startswith(sp) for sp in sub_paths)
            ]
        for sub_url in sub_links:
            sub_cached = get_cached_content(sub_url)
            if sub_cached and is_cache_valid(sub_cached):
                sub_formatted = _format_cached_content(sub_url, sub_cached)
                if sub_formatted:
                    context_parts.append(sub_formatted)
            else:
                print(f"    [sub-fetch] {sub_url}")
                try:
                    sub_data = fetch_url(sub_url)
                    if "error" not in sub_data:
                        cache_content(sub_url, sub_data)
                        sub_formatted = _format_cached_content(sub_url, sub_data)
                        if sub_formatted:
                            context_parts.append(sub_formatted)
                except Exception as e:
                    print(f"    [sub-error] {sub_url}: {e}")

    if context_parts:
        return "\n\n---\n\n".join(context_parts)

    return ""


def main():
    import argparse

    parser = argparse.ArgumentParser(description="URL Cache Manager for Drupal Tips")
    parser.add_argument("--fetch", action="store_true", help="Fetch all category URLs")
    parser.add_argument(
        "--fetch-category",
        type=int,
        metavar="N",
        help="Fetch URLs for specific category",
    )
    parser.add_argument(
        "--force", action="store_true", help="Force re-fetch even if cached"
    )
    parser.add_argument("--list", action="store_true", help="List cached URLs")
    parser.add_argument("--clear", action="store_true", help="Clear all cached data")

    args = parser.parse_args()

    if args.clear:
        import shutil

        if CACHE_DIR.exists():
            shutil.rmtree(CACHE_DIR)
            print(f"Cleared cache directory: {CACHE_DIR}")
        else:
            print("Cache directory does not exist")
        return

    if args.list:
        if not CACHE_DIR.exists():
            print("No cached data found")
            return

        files = list(CACHE_DIR.iterdir())
        if not files:
            print("No cached data found")
            return

        print(f"Cached files in {CACHE_DIR}:")
        for f in sorted(files):
            stat = f.stat()
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            print(f"  {f.name} ({stat.st_size} bytes, {mtime})")
        return

    if args.fetch:
        print("Fetching data for all categories with URLs...")
        results = fetch_all_category_data(force=args.force)
        total = sum(len(paths) for paths in results.values())
        print(f"\nDone! Cached {total} files.")
        return

    if args.fetch_category:
        from tip_generator import CATEGORIES

        if args.fetch_category not in CATEGORIES:
            print(f"Category {args.fetch_category} not found")
            return

        cat_info = CATEGORIES[args.fetch_category]
        print(f"Fetching URLs for category {args.fetch_category}: {cat_info['name']}")
        cached = fetch_category_urls(args.fetch_category, cat_info, force=args.force)
        print(f"\nCached {len(cached)} files")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
