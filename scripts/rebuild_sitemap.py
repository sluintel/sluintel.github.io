#!/usr/bin/env python3
"""
rebuild_sitemap.py — Standalone sitemap rebuilder.
No external dependencies. Run from repo root:
    python3 scripts/rebuild_sitemap.py
"""
import json
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT    = Path(__file__).parent.parent
POSTS_JSON   = REPO_ROOT / "posts.json"
SITEMAP_PATH = REPO_ROOT / "sitemap.xml"
SITE_URL     = "https://sluintel.github.io"

CATEGORY_SLUGS = [
    "trending", "ai-automation", "sports", "finance",
    "entertainment", "technology", "deep-dives", "all",
]

def main():
    # Load posts
    posts = json.loads(POSTS_JSON.read_text(encoding="utf-8"))
    print(f"Loaded {len(posts)} posts from posts.json")

    # Deduplicate by URL
    seen_urls = set()
    unique_posts = []
    for p in posts:
        url = p.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_posts.append(p)

    dupes = len(posts) - len(unique_posts)
    if dupes:
        print(f"Removed {dupes} duplicate URLs")

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    def url_block(loc, lastmod, changefreq, priority):
        return (
            f"  <url>\n"
            f"    <loc>{loc}</loc>\n"
            f"    <lastmod>{lastmod}</lastmod>\n"
            f"    <changefreq>{changefreq}</changefreq>\n"
            f"    <priority>{priority}</priority>\n"
            f"  </url>"
        )

    blocks = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
        '        xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9',
        '          http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">',
        url_block(f"{SITE_URL}/", now_iso, "daily", "1.00"),
    ]

    # Category pages
    for slug in CATEGORY_SLUGS:
        blocks.append(url_block(
            f"{SITE_URL}/category/{slug}", now_iso, "daily", "0.90"
        ))

    # Posts with real lastmod dates
    for p in unique_posts:
        date_str = p.get("date", "")
        try:
            lastmod = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%dT00:00:00+00:00")
        except (ValueError, TypeError):
            lastmod = now_iso
        blocks.append(url_block(
            f"{SITE_URL}/{p['url']}", lastmod, "weekly", "0.80"
        ))

    blocks.append("</urlset>")
    sitemap = "\n".join(blocks) + "\n"

    # Write — plain UTF-8, no BOM
    SITEMAP_PATH.write_text(sitemap, encoding="utf-8")

    total_urls = 1 + len(CATEGORY_SLUGS) + len(unique_posts)
    print(f"sitemap.xml written — {total_urls} URLs total")
    print(f"  Homepage:        1")
    print(f"  Category pages:  {len(CATEGORY_SLUGS)}")
    print(f"  Posts:           {len(unique_posts)}")

if __name__ == "__main__":
    main()
