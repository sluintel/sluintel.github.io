#!/usr/bin/env python3
"""
suggest_titles.py — Given a keyword, generate 5 compelling blog post titles
using Gemini AI and save them to pending_approval.json.

Usage:
    python scripts/suggest_titles.py --keyword "Claude AI vs ChatGPT"

GitHub Actions reads the titles from the log, then the user triggers
publish_approved.yml with their chosen title number or a custom title.
"""

import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from google import genai
from google.genai import types

REPO_ROOT         = Path(__file__).parent.parent
PENDING_FILE      = REPO_ROOT / "pending_approval.json"
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY", "")


def generate_titles(keyword: str) -> list[str]:
    """Ask Gemini for 5 distinct, SEO-optimised title options."""
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""You are an expert SEO content strategist for a blog about AI tools, automation, sports, finance, entertainment, and trending topics.

A blog post needs to be written about: "{keyword}"

Generate exactly 5 distinct, compelling blog post title options.

Rules:
- Each title must be under 65 characters (ideal for Google SERPs)
- Include the primary keyword or a close variant naturally
- Each title should use a different angle or style:
  Option 1: Direct / informational ("What is X / How X Works")
  Option 2: Listicle or guide ("5 Ways X / Your Guide to X")
  Option 3: Trending / curiosity ("Why X Is Trending / What People Are Saying About X")  
  Option 4: Benefit-led ("How X Can Help You / Why You Need to Know About X")
  Option 5: Bold / opinionated ("X Is Changing Everything / The Truth About X")
- Avoid: clickbait, false promises, all-caps, exclamation marks
- Avoid starting with: "Unlocking", "Unleashing", "Mastering", "Decoding"

Return ONLY a valid JSON array of exactly 5 strings, no markdown, no explanation:
["Title 1", "Title 2", "Title 3", "Title 4", "Title 5"]"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        ),
    )

    titles = json.loads(response.text)
    if not isinstance(titles, list) or len(titles) != 5:
        raise ValueError(f"Gemini returned unexpected format: {response.text[:200]}")
    return [str(t).strip() for t in titles]


def main():
    parser = argparse.ArgumentParser(description="Generate 5 title suggestions for a keyword")
    parser.add_argument("--keyword", required=True, help="The topic/keyword to generate titles for")
    args = parser.parse_args()

    keyword = args.keyword.strip()
    print(f"\n🔍 Generating 5 title suggestions for: \"{keyword}\"\n")

    titles = generate_titles(keyword)

    # ── Print to Actions log (this is how the user reads them) ──────────────
    print("=" * 60)
    print("📝 TITLE SUGGESTIONS — pick one and trigger publish_approved.yml")
    print("=" * 60)
    for i, title in enumerate(titles, 1):
        chars = len(title)
        seo   = "✅" if chars <= 65 else "⚠️ "
        print(f"\n  [{i}] {seo} {title}")
        print(f"       ({chars} chars)")
    print("\n" + "=" * 60)
    print("  Or enter your own custom title in publish_approved.yml")
    print("=" * 60 + "\n")

    # ── Save to pending_approval.json so it's visible in the repo too ───────
    pending = {
        "keyword":    keyword,
        "generated":  datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "titles":     titles,
        "instruction": (
            "Trigger publish_approved.yml — set 'title_choice' to 1-5 "
            "to pick one of the above, or type your own custom title."
        ),
    }
    PENDING_FILE.write_text(json.dumps(pending, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Saved to pending_approval.json")
    print(f"   Now trigger publish_approved.yml with:")
    print(f"   keyword = \"{keyword}\"")
    print(f"   title_choice = 1, 2, 3, 4, or 5 (or your own title text)\n")


if __name__ == "__main__":
    main()
