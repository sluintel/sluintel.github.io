#!/usr/bin/env python3
"""
Sujit Luintel's AI Assisted Blog Generator
Niche: AI Tools & Automation
Runs daily via GitHub Actions
"""

import os
import io
import sys
import json
import re
import time
import random
import hashlib
import textwrap
import argparse
import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from google import genai

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
REPO_ROOT    = Path(__file__).parent.parent
POSTS_DIR    = REPO_ROOT / "posts"
OG_DIR       = REPO_ROOT / "posts" / "og"
POSTS_JSON   = REPO_ROOT / "posts.json"
POSTS_DATA_JSON = REPO_ROOT / "assets" / "js" / "posts-data.json"
USED_KW_FILE = REPO_ROOT / "used_keywords.json"
INDEX_HTML   = REPO_ROOT / "index.html"
SITEMAP_PATH = REPO_ROOT / "sitemap.xml"
LLMS_PATH    = REPO_ROOT / "llms.txt"
RSS_PATH     = REPO_ROOT / "feed.xml"
ROBOTS_PATH  = REPO_ROOT / "robots.txt"

SITE_URL       = "https://sluintel.github.io"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
UNSPLASH_KEY   = os.environ.get("UNSPLASH_ACCESS_KEY", "")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY","")

FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

FALLBACK_KEYWORDS = [
    "best AI tools 2026",
    "AI automation for small business",
    "ChatGPT vs Claude vs Gemini",
    "no-code automation tools review",
    "AI writing tools comparison",
    "workflow automation with AI",
    "free AI image generation tools",
    "AI productivity tools for remote work",
    "how to automate your business with AI",
    "top AI SEO tools 2026",
    "AI tools for content creators",
    "make money with AI automation",
    "AI agents explained simply",
    "Zapier vs Make vs n8n comparison",
    "best AI code assistants 2026",
    "AI tools for email marketing",
    "how to use Claude AI effectively",
    "AI research tools for students",
    "AI video generation tools",
    "machine learning without coding",
    "best AI chatbot builders for business",
    "AI tools for social media marketing 2026",
    "AI voice generator tools comparison",
    "how to build AI workflows without coding",
    "OpenAI API tutorial for beginners",
    "best AI tools for data analysis",
    "AI transcription tools review 2026",
    "AI customer service automation guide",
    "prompt engineering tips for better results",
    "best AI tools for freelancers 2026",
    "local AI models vs cloud AI pros cons",
    "best AI text summarization tools",
    "AI tools for project management 2026",
    "how to use AI for keyword research SEO",
    "n8n automation tutorials for beginners",
    "AI tools for podcast creation and editing",
    "Perplexity AI vs ChatGPT which is better",
    "AI tools for e-commerce store automation",
    "Claude AI API tutorial for developers",
    "how to use AI to write better blog posts",
]

AI_TECH_TERMS = {
    "ai", "artificial intelligence", "chatgpt", "claude", "gemini",
    "openai", "llm", "automation", "robot", "machine learning",
    "gpt", "copilot", "midjourney", "stable diffusion", "tool",
    "software", "app", "tech", "digital", "model", "agent",
    "workflow", "productivity", "coding", "developer", "data",
    "perplexity", "sora", "dall-e", "whisper", "hugging face",
    "langchain", "rag", "vector", "neural", "deep learning",
}

TRENDS_RSS_FEEDS = [
    ("NP", "https://trends.google.com/trending/rss?geo=NP"),
    ("US", "https://trends.google.com/trending/rss?geo=US"),
    ("GB", "https://trends.google.com/trending/rss?geo=GB"),
    ("IN", "https://trends.google.com/trending/rss?geo=IN"),
    ("AU", "https://trends.google.com/trending/rss?geo=AU"),
    ("CA", "https://trends.google.com/trending/rss?geo=CA"),
]

# ─────────────────────────────────────────
# 1. KEYWORD RESEARCH
# ─────────────────────────────────────────

AI_TECH_TEMPLATES = [
    "how AI is transforming {}",
    "the future of {} with AI",
    "AI breakthroughs related to {}",
    "how automation is changing {}",
    "AI-powered innovations in {}",
    "the rise of AI in {}",
    "how generative AI is impacting {}",
    "best AI tools for {}",
]

SPORTS_TEMPLATES = [
    "{} latest updates and predictions",
    "why {} is trending in sports right now",
    "everything happening around {}",
    "top reactions to {}",
    "{} highlights fans are talking about",
    "what's next for {}",
]

ENTERTAINMENT_TEMPLATES = [
    "why {} is breaking the internet",
    "{} latest buzz and fan reactions",
    "everything to know about {}",
    "why everyone is talking about {}",
    "{} moments trending worldwide",
    "the latest story behind {}",
]

GENERAL_TEMPLATES = [
    "why {} is trending right now",
    "everything you should know about {}",
    "the latest updates on {}",
    "what people are saying about {}",
    "{} explained simply",
    "top internet reactions to {}",
]

SPORTS_KEYWORDS = {
    "football", "cricket", "fifa", "nba", "ipl", "world cup",
    "match", "goal", "ronaldo", "messi", "virat", "dhoni",
    "sports", "tennis", "wwe", "ufc", "champions",
    "league", "cup", "tournament", "fc"
}

ENTERTAINMENT_KEYWORDS = {
    "movie", "film", "netflix", "series", "celebrity",
    "actor", "actress", "hollywood", "bollywood",
    "music", "song", "album", "concert", "youtube",
    "instagram", "tiktok", "anime", "show",
    "rapper", "singer", "podcast"
}


def load_used_keywords():
    if USED_KW_FILE.exists():
        try:
            content = USED_KW_FILE.read_text().strip()
            if content:
                return json.loads(content)
        except (json.JSONDecodeError, ValueError):
            print("used_keywords.json was malformed — resetting it")
    return []


def save_used_keyword(kw):
    used = load_used_keywords()
    used.append(kw)
    USED_KW_FILE.write_text(json.dumps(used[-80:], indent=2))


def _is_ai_tech(text: str) -> bool:
    words = set(re.findall(r"[a-z0-9]+", text.lower()))
    return bool(words & AI_TECH_TERMS)


def clean_topic(title: str) -> str:
    title = re.sub(r"\b(2024|2025|2026)\b", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def detect_category(keyword: str) -> str:
    text = keyword.lower()
    if any(word in text for word in AI_TECH_TERMS):
        return "tech"
    if any(word in text for word in SPORTS_KEYWORDS):
        return "sports"
    if any(word in text for word in ENTERTAINMENT_KEYWORDS):
        return "entertainment"
    return "general"


def generate_dynamic_title(keyword: str) -> str:
    topic = clean_topic(keyword)
    category = detect_category(topic)
    if category == "tech":
        template = random.choice(AI_TECH_TEMPLATES)
    elif category == "sports":
        template = random.choice(SPORTS_TEMPLATES)
    elif category == "entertainment":
        template = random.choice(ENTERTAINMENT_TEMPLATES)
    else:
        template = random.choice(GENERAL_TEMPLATES)
    title = template.format(topic)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def fetch_trends_rss(geo: str, url: str) -> list:
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; SluIntelBot/1.0; +https://sluintel.github.io)"},
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"Trends RSS ({geo}): HTTP {resp.status_code}")
            return []
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")
        titles = []
        for item in items:
            title_el = item.find("title")
            if title_el is not None and title_el.text:
                titles.append(title_el.text.strip())
        return titles
    except ET.ParseError as e:
        print(f"Trends RSS ({geo}): XML parse error — {e}")
        return []
    except requests.RequestException as e:
        print(f"Trends RSS ({geo}): request error — {e}")
        return []


def get_trending_keyword() -> str:
    all_titles = []
    for geo, url in TRENDS_RSS_FEEDS:
        titles = fetch_trends_rss(geo, url)
        for title in titles:
            if _is_ai_tech(title):
                print(f"Trending AI/Tech RSS ({geo}): {title}")
                save_used_keyword(title)
                return title
        for title in titles:
            all_titles.append((geo, title))
    if all_titles:
        geo, title = random.choice(all_titles[:10])
        reframed = generate_dynamic_title(title)
        print(f"Reframed trending topic ({geo}): {reframed}")
        save_used_keyword(reframed)
        return reframed
    used = load_used_keywords()
    available = [k for k in FALLBACK_KEYWORDS if k not in used]
    if not available:
        print("ℹ️  All fallback keywords used — resetting pool")
        USED_KW_FILE.write_text(json.dumps([], indent=2))
        available = FALLBACK_KEYWORDS
    kw = random.choice(available)
    save_used_keyword(kw)
    print(f"Fallback keyword: {kw}")
    return kw


# ─────────────────────────────────────────
# 2. INTERNAL LINKING HELPERS
# ─────────────────────────────────────────

_STOP_TAGS = {
    "ai tools", "automation", "ai", "tools", "future of work",
    "2026 trends", "productivity", "digital transformation",
    "tech trends", "future tech", "ai automation",
}


def _tokenise(text: str) -> set:
    return {w for w in re.split(r"\W+", text.lower()) if len(w) > 1}


def _build_posts_index() -> list:
    posts = load_posts()
    seen_slugs = set()
    index = []
    for p in posts:
        slug = p.get("slug", "")
        if not slug or slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        index.append({
            "title":   p.get("title", ""),
            "slug":    slug,
            "url":     p.get("url", f"posts/{slug}.html"),
            "tags":    [t.lower() for t in p.get("tags", [])],
            "keyword": p.get("keyword", ""),
        })
    return index


def _score_relevance(post: dict, kw_tokens: set, used_keywords: list) -> int:
    score = 0
    score += len(kw_tokens & _tokenise(post["title"])) * 3
    if post["keyword"]:
        score += len(kw_tokens & _tokenise(post["keyword"])) * 4
    meaningful_tags = [t for t in post["tags"] if t not in _STOP_TAGS]
    score += len(kw_tokens & _tokenise(" ".join(meaningful_tags))) * 2
    for used_kw in used_keywords:
        if len(kw_tokens & _tokenise(used_kw)) >= 2:
            score += 1
    return score


def _select_link_candidates(posts_index, current_keyword, used_keywords, max_links=6, min_score=2):
    kw_tokens = _tokenise(current_keyword)
    scored = [
        (s, p)
        for p in posts_index
        if (s := _score_relevance(p, kw_tokens, used_keywords)) >= min_score
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:max_links]]


def _build_linking_prompt_block(candidates: list) -> str:
    if not candidates:
        return ""
    lines = [
        f'  - href="/{p["url"]}" | Title: "{p["title"]}"'
        for p in candidates
    ]
    return (
        "\n━━━ INTERNAL LINKING (MANDATORY) ━━━\n"
        "Embed 2–4 natural internal links inside the post body using ONLY the exact hrefs listed below.\n\n"
        "Rules:\n"
        "- Anchor text must be descriptive and contextually relevant — NEVER \"click here\" or \"read more\"\n"
        "- Place <a> tags inside <p> or <li> elements only — NEVER inside headings\n"
        "- Spread links across different sections (not all clustered in one paragraph)\n"
        "- Do NOT invent, modify, or shorten any href — use the full path exactly as given\n"
        "- If fewer than 2 posts are genuinely relevant, only add those that truly fit\n\n"
        "Approved internal links:\n"
        + "\n".join(lines)
        + "\n"
    )


def _validate_links(html: str, valid_urls: set) -> str:
    def _fix(match):
        href  = match.group(1).lstrip("/")
        inner = match.group(2)
        if href in valid_urls:
            return match.group(0)
        print(f"Stripped hallucinated link: {match.group(1)}")
        return inner
    return re.sub(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>', _fix, html, flags=re.DOTALL)


# ─────────────────────────────────────────
# 3. GENERATE BLOG POST WITH GEMINI
# ─────────────────────────────────────────

def _gemini_with_retry(client, model, contents, config, max_attempts: int = 3):
    """Call Gemini with exponential backoff on transient failures."""
    for attempt in range(1, max_attempts + 1):
        try:
            return client.models.generate_content(
                model=model, contents=contents, config=config
            )
        except Exception as exc:
            if attempt == max_attempts:
                raise
            wait = 2 ** attempt
            print(f"Gemini attempt {attempt}/{max_attempts} failed: {exc}")
            print(f"   Retrying in {wait}s…")
            time.sleep(wait)


def _validate_post(data: dict) -> None:
    """Warn about SEO / quality issues without blocking publish."""
    plain = re.sub(r"<[^>]+>", " ", data.get("content_html", ""))
    word_count = len(plain.split())
    title_len  = len(data.get("title", ""))
    meta_len   = len(data.get("meta_description", ""))

    print(f"  Word count       : ~{word_count}")
    print(f"  Title length     : {title_len} chars")
    print(f"  Meta desc length : {meta_len} chars")

    if word_count < 600:
        print(f"Content is short ({word_count} words) — consider regenerating")
    if title_len > 65:
        print(f"Title exceeds 65 chars — may be truncated in SERPs")
    if meta_len > 160:
        print(f"Meta description exceeds 160 chars")
    if not data.get("slug"):
        print("Empty slug — will use fallback")


def _unique_slug(slug: str, date_str: str) -> str:
    """Append -2, -3 … if a post file for this date+slug already exists."""
    base    = slug
    counter = 2
    while (POSTS_DIR / f"{date_str}-{slug}.html").exists():
        slug = f"{base}-{counter}"
        counter += 1
    if slug != base:
        print(f"Slug collision — renamed to '{slug}'")
    return slug




def _safe_parse_gemini_json(raw: str) -> dict:
    """
    Robustly parse JSON from Gemini even when content_html contains
    unescaped quotes, newlines, or other characters that break json.loads.
    Strategy:
      1. Try json.loads directly (fastest path).
      2. Strip markdown fences and retry.
      3. Extract content_html separately, replace it with a placeholder,
         parse the rest cleanly, then re-insert the HTML.
      4. If all else fails, raise with a clear message.
    """
    # ── Pass 1: direct parse ──────────────────────────────────────────────
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # ── Pass 2: strip markdown fences ────────────────────────────────────
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"```$", "", cleaned.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # ── Pass 3: extract content_html separately ───────────────────────────
    # Find the value of "content_html" using a greedy search between the key
    # and the closing }" of the top-level object.
    html_match = re.search(
        r'"content_html"\s*:\s*"(.*?)"\s*\}?\s*$',
        cleaned,
        re.DOTALL,
    )
    if html_match:
        html_value  = html_match.group(1)
        placeholder = "__CONTENT_HTML_PLACEHOLDER__"
        stub        = cleaned[: html_match.start()] + f'"content_html": "{placeholder}"' + "}"
        try:
            data = json.loads(stub)
            # Unescape the raw HTML value (Gemini sometimes double-escapes)
            data["content_html"] = html_value.replace(chr(92)+chr(34), chr(34))

            return data
        except json.JSONDecodeError:
            pass

    # ── Pass 4: use Gemini again with stricter prompt ─────────────────────
    print("⚠️  JSON parse failed on all passes — attempting Gemini repair call…")
    try:
        from google import genai as _genai
        from google.genai import types as _types
        _client = _genai.Client(api_key=GEMINI_API_KEY)
        repair_prompt = (
            "The following text is a malformed JSON object. "
            "Fix it so it is valid JSON and return ONLY the fixed JSON, "
            "no markdown, no explanation:\n\n" + raw[:8000]
        )
        repair_resp = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=repair_prompt,
            config=_types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return json.loads(repair_resp.text)
    except Exception as e:
        print(f"⚠️  Gemini repair also failed: {e}")

    raise ValueError(
        f"Could not parse Gemini JSON response after all recovery attempts. "
        f"First 300 chars: {raw[:300]}"
    )


def generate_blog_post(keyword: str) -> dict:
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)

    posts_index   = _build_posts_index()
    used_keywords = load_used_keywords()
    candidates    = _select_link_candidates(posts_index, keyword, used_keywords)
    valid_urls    = {p["url"] for p in posts_index} | {p["url"].lstrip("/") for p in posts_index}
    linking_block = _build_linking_prompt_block(candidates)

    if candidates:
        print(f"🔗 Internal link candidates ({len(candidates)}):")
        for c in candidates:
            print(f"   → {c['title']}")
    else:
        print("ℹ️  No relevant internal link candidates for this keyword")

    prompt = f"""You are an expert SEO content strategist and tech blogger specialising in AI tools and automation. Your articles consistently rank on Google page 1 because you understand both search intent and reader psychology.

Write a comprehensive, SEO-optimised blog post about: "{keyword}"

━━━ CONTENT STRUCTURE (follow exactly) ━━━

1. INTRO (80-120 words)
   - Open with a relatable problem, surprising stat, or bold opinion — NOT "In today's digital world"
   - Clearly state what the reader will learn
   - Include the primary keyword naturally in the first 100 words

2. SECTION 1 — "What Is / Why It Matters" (h2)
   - Define the topic clearly for beginners
   - Explain why it matters RIGHT NOW in 2026
   - 1 short paragraph + 3-4 bullet points

3. SECTION 2 — Core Value Section (h2) — the meat
   - The most important practical information
   - Use h3 subheadings to break it down
   - Include at least one bullet list

4. SECTION 3 — How-To or Deep Dive (h2)
   - Step-by-step guidance OR a detailed comparison/breakdown
   - Numbered list or structured bullet points
   - Be specific — no vague advice

5. SECTION 4 — Pro Tips / Common Mistakes (h2)
   - 4-6 bullet points of actionable insider tips
   - OR 3-4 common mistakes people make and how to avoid them
   - This is where you show opinion and expertise

6. SECTION 5 — Tools / Resources (h2) [include only if relevant]
   - Mention 3-5 specific real tools, platforms, or resources
   - One sentence on what each does and who it's best for

7. CONCLUSION (60-80 words)
   - Summarise the key takeaway in 1-2 sentences
   - End with a forward-looking statement or motivating CTA
   - Do NOT start with "In conclusion"

━━━ SEO RULES ━━━
- Primary keyword must appear in: intro paragraph, at least 2 h2 headings, and conclusion
- Use semantic/LSI keywords naturally throughout (do NOT stuff)
- Every h2 must be compelling enough to standalone as a social media headline
- Sentences: mix short punchy ones with longer explanatory ones
- Paragraphs: max 3-4 lines — never a wall of text
- Total word count: 950-1150 words
- Reading level: clear and accessible — avoid corporate jargon

━━━ WRITING STYLE ━━━
- Voice: knowledgeable friend, not textbook author
- Tone: clear, practical, slightly opinionated — take a stance
- Use "you" to address the reader directly
- Contractions are fine (it's, you'll, don't)
- Avoid: "In today's fast-paced world", "game-changer", "leverage", "delve", "it's worth noting"
- Allowed: strong claims backed by logic, honest pros/cons, specific examples

━━━ HTML FORMATTING ━━━
- Use: h2, h3, p, ul, li, ol, strong, em, blockquote, a
- Do NOT include: h1, img, the post title, feature image, or any inline styles
- Wrap key terms or takeaways in <strong> for emphasis
- Use <blockquote> for a key stat or standout quote (1 per post max)
- Use <em> sparingly for genuine emphasis only
{linking_block}
Return ONLY a valid JSON object with exactly these keys — no markdown fences, no preamble:
{{
  "title": "Compelling title under 65 chars — include primary keyword near the start",
  "meta_description": "155 chars max — include keyword, state the benefit, create curiosity",
  "slug": "primary-keyword-slug-hyphens-only-no-special-chars",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "reading_time": "X min read",
  "content_html": "<p>Full post HTML here...</p>"
}}"""

    response = _gemini_with_retry(
        client,
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )

    data = _safe_parse_gemini_json(response.text)

    data["slug"] = re.sub(r"[^a-z0-9\-]", "", data["slug"].lower().replace(" ", "-"))
    data["slug"] = re.sub(r"-+", "-", data["slug"]).strip("-")
    if not data["slug"]:
        data["slug"] = re.sub(r"[^a-z0-9\-]", "-", keyword.lower())[:60].strip("-")

    data["keyword"] = keyword

    if valid_urls:
        data["content_html"] = _validate_links(data["content_html"], valid_urls)

    links_found = re.findall(r'<a href=', data["content_html"])
    print(f"Post generated: {data['title']}")
    print(f" Internal links embedded: {len(links_found)}")
    _validate_post(data)
    return data


# ─────────────────────────────────────────
# 4. FETCH FEATURE IMAGE
# ─────────────────────────────────────────

def _build_credit(name, profile_url, platform, platform_url):
    return (
        f'Photo by <a href="{profile_url}" target="_blank" rel="noopener">{name}</a>'
        f' on <a href="{platform_url}" target="_blank" rel="noopener">{platform}</a>'
    )


def _keyword_hash_page(keyword: str, total_pages: int = 8) -> int:
    h = int(hashlib.md5(keyword.lower().encode()).hexdigest(), 16)
    return (h % total_pages) + 1


def _build_queries(keyword: str) -> list:
    words = keyword.split()
    if "vs" in keyword.lower():
        teams = [w for w in words if w.lower() != "vs" and not w.isdigit()]
        queries = [
            " ".join(teams[:2]) + " sport action",
            " ".join(teams[:2]),
            "sport action stadium crowd",
        ]
    elif "how ai" in keyword.lower() or "ai is" in keyword.lower():
        subject = " ".join(words[-3:])
        queries = [
            subject + " technology",
            subject,
            "artificial intelligence technology digital",
            "data analytics technology future",
        ]
    else:
        base4 = " ".join(words[:4])
        base2 = " ".join(words[:2])
        queries = [
            base4 + (" technology AI" if _is_ai_tech(keyword) else ""),
            base4,
            base2,
            "artificial intelligence technology" if _is_ai_tech(keyword) else "business productivity",
        ]
    seen, unique = set(), []
    for q in queries:
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            unique.append(q)
    return unique


def _pexels(query: str, keyword: str, api_key: str):
    if not api_key:
        return None
    page = _keyword_hash_page(keyword, total_pages=8)
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            params={"query": query, "orientation": "landscape", "per_page": 15, "page": page, "size": "large"},
            headers={"Authorization": api_key},
            timeout=10,
        )
        if r.status_code != 200:
            print(f" Pexels HTTP {r.status_code} for '{query}' page {page}")
            return None
        photos = r.json().get("photos", [])
        if not photos:
            return None
        photo = random.choice(photos)
        return (
            photo["src"]["large2x"],
            _build_credit(photo["photographer"], photo["photographer_url"], "Pexels", "https://www.pexels.com"),
        )
    except Exception as e:
        print(f" Pexels error: {e}")
        return None


def _unsplash(query: str, keyword: str, api_key: str):
    if not api_key:
        return None
    page = _keyword_hash_page(keyword, total_pages=5)
    try:
        r = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": query, "orientation": "landscape", "content_filter": "high",
                    "per_page": 15, "page": page, "order_by": "relevant"},
            headers={"Authorization": f"Client-ID {api_key}"},
            timeout=10,
        )
        if r.status_code != 200:
            print(f"  Unsplash HTTP {r.status_code} for '{query}' page {page}")
            return None
        results = r.json().get("results", [])
        if not results:
            return None
        photo = random.choice(results)
        return (
            photo["urls"]["regular"],
            _build_credit(
                photo["user"]["name"],
                photo["links"]["html"] + "?utm_source=sluintel&utm_medium=referral",
                "Unsplash",
                "https://unsplash.com?utm_source=sluintel&utm_medium=referral",
            ),
        )
    except Exception as e:
        print(f" Unsplash error: {e}")
        return None


def _openverse(query: str, keyword: str):
    page = _keyword_hash_page(keyword, total_pages=6)
    try:
        r = requests.get(
            "https://api.openverse.org/v1/images/",
            params={"q": query, "license_type": "commercial", "aspect_ratio": "wide",
                    "page_size": 15, "page": page, "mature": "false"},
            headers={"User-Agent": "SluIntelBot/1.0 (https://sluintel.github.io)"},
            timeout=10,
        )
        if r.status_code != 200:
            print(f" Openverse HTTP {r.status_code} for '{query}' page {page}")
            return None
        results = r.json().get("results", [])
        if not results:
            return None
        photo = random.choice(results)
        return (
            photo["url"],
            _build_credit(
                photo.get("creator") or "photographer",
                photo.get("creator_url") or "https://openverse.org",
                "Openverse",
                photo.get("foreign_landing_url") or "https://openverse.org",
            ),
        )
    except Exception as e:
        print(f" Openverse error: {e}")
        return None


def get_feature_image(keyword: str):
    FALLBACK_IMAGES = [
        "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=1200&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=1200&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1655720031554-a929595ffad7?w=1200&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1676299081847-824916de030a?w=1200&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=1200&auto=format&fit=crop",
    ]
    PEXELS_KEY   = os.environ.get("PEXELS_API_KEY", "")
    UNSPLASH_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")

    queries = _build_queries(keyword)
    sources = [
        ("Pexels",    lambda q: _pexels(q, keyword, PEXELS_KEY)),
        ("Openverse", lambda q: _openverse(q, keyword)),
        ("Unsplash",  lambda q: _unsplash(q, keyword, UNSPLASH_KEY)),
    ]
    for source_name, fetcher in sources:
        for query in queries:
            result = fetcher(query)
            if result:
                img_url, credit = result
                print(f" [{source_name}] Image fetched for '{query}' (keyword: '{keyword}')")
                return img_url, credit
            print(f"↩️  [{source_name}] No result for '{query}', trying next…")

    idx    = _keyword_hash_page(keyword, total_pages=len(FALLBACK_IMAGES)) - 1
    img    = FALLBACK_IMAGES[idx]
    credit = 'Photo from <a href="https://unsplash.com" target="_blank" rel="noopener">Unsplash</a>'
    print(" All sources failed — using hardcoded fallback image")
    return img, credit


# ─────────────────────────────────────────
# 5. GENERATE OG IMAGE (1200×630)
# ─────────────────────────────────────────
def generate_og_image(title: str, slug: str) -> str:
    OG_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OG_DIR / f"{slug}.png"
    W, H = 1200, 630

    bg   = Image.new("RGB", (W, H), (10, 10, 20))
    draw = ImageDraw.Draw(bg)
    for y in range(H):
        t = y / H
        draw.rectangle([(0, y), (W, y + 1)], fill=(
            int(12 + t * 8), int(12 + t * 6), int(28 + t * 18),
        ))
    draw.rectangle([(0, 0), (7, H)], fill=(99, 102, 241))
    for gx in range(60, W, 60):
        for gy in range(60, H, 60):
            draw.ellipse([(gx - 1, gy - 1), (gx + 1, gy + 1)], fill=(255, 255, 255, 15))

    try:
        badge_font = ImageFont.truetype(FONT_BOLD, 26)
    except Exception:
        badge_font = ImageFont.load_default()
    draw.rounded_rectangle([(48, 44), (375, 92)], radius=8, fill=(99, 102, 241))
    draw.text((68, 54), "sluintel.github.io", font=badge_font, fill="white")

    try:
        title_font = ImageFont.truetype(FONT_BOLD, 60)
    except Exception:
        title_font = ImageFont.load_default()

    max_chars = 24
    lines     = textwrap.wrap(title, width=max_chars)[:3]
    line_h    = 76
    total_h   = len(lines) * line_h
    y_start   = max(130, (H - 80 - total_h) // 2)

    for i, line in enumerate(lines):
        draw.text((62, y_start + i * line_h + 2), line, font=title_font, fill=(0, 0, 0, 120))
        draw.text((60, y_start + i * line_h),     line, font=title_font, fill="white")

    if len(textwrap.wrap(title, width=max_chars)) > 3:
        draw.text((60, y_start + 2 * line_h), lines[2].rstrip() + "…", font=title_font, fill="white")

    draw.rectangle([(0, H - 72), (W, H)], fill=(18, 18, 35))
    try:
        tag_font = ImageFont.truetype(FONT_REG, 24)
    except Exception:
        tag_font = ImageFont.load_default()
    draw.text((60, H - 50), "AI Tools & Automation Insights  ·  Sujit Luintel", font=tag_font, fill=(160, 160, 210))

    for cx, cy, cr, alpha in [(1050, 180, 120, 18), (1120, 420, 80, 12), (980, 500, 50, 10)]:
        circle_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cd = ImageDraw.Draw(circle_layer)
        cd.ellipse([(cx - cr, cy - cr), (cx + cr, cy + cr)], outline=(99, 102, 241, alpha), width=2)
        bg = Image.alpha_composite(bg.convert("RGBA"), circle_layer).convert("RGB")
        draw = ImageDraw.Draw(bg)

    bg.save(str(out_path), "PNG", optimize=True)
    og_url = f"{SITE_URL}/posts/og/{slug}.png"
    print(f"OG image saved → posts/og/{slug}.png")
    return og_url


# ─────────────────────────────────────────
# 6. BUILD POST HTML FILE  ← NEW DESIGN
# ─────────────────────────────────────────

_POST_CSS = """
/* ═══ TOKENS ═══ */
:root {
  --font-display: 'Playfair Display', Georgia, serif;
  --font-body:    'DM Sans', system-ui, sans-serif;
  --bg:           #0d0d0f; --bg-2: #141417; --bg-3: #1a1a1f;
  --surface:      #1e1e24; --surface-2: #26262e;
  --border:       rgba(255,255,255,0.08); --border-2: rgba(255,255,255,0.14);
  --text:         #f0f0f4; --text-2: #a8a8b8; --text-3: #6b6b7d;
  --accent:       #6366f1; --accent-2: #8b5cf6;
  --accent-glow:  rgba(99,102,241,0.25);
  --radius:       10px; --shadow: 0 4px 24px rgba(0,0,0,0.4);
}
[data-theme="light"] {
  --bg: #f8f8fc; --bg-2: #f0f0f8; --bg-3: #e8e8f4;
  --surface: #ffffff; --surface-2: #f4f4f9;
  --border: rgba(0,0,0,0.08); --border-2: rgba(0,0,0,0.14);
  --text: #0d0d1a; --text-2: #4a4a6a; --text-3: #8888aa;
  --accent-glow: rgba(99,102,241,0.12);
  --shadow: 0 2px 12px rgba(0,0,0,0.08);
}
/* ═══ RESET ═══ */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: var(--font-body); background: var(--bg); color: var(--text); line-height: 1.7; }
a    { color: inherit; text-decoration: none; }
img  { display: block; max-width: 100%; }
/* ═══ NAV ═══ */
.sl-nav {
  position: sticky; top: 0; z-index: 1000;
  background: var(--bg); border-bottom: 1px solid var(--border);
  backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
}
.sl-nav__inner {
  max-width: 1200px; margin: 0 auto; display: flex; align-items: center;
  padding: 0 24px; height: 58px; position: relative;
}
.sl-nav__brand {
  font-family: var(--font-display); font-size: 1.4rem; font-weight: 900;
  color: var(--text); white-space: nowrap; margin-right: 24px; flex-shrink: 0;
}
.sl-nav__brand span { color: var(--accent); }
.sl-nav__links {
  display: flex; align-items: center; gap: 2px; flex: 1;
  overflow-x: auto; scrollbar-width: none;
}
.sl-nav__links::-webkit-scrollbar { display: none; }
.sl-nav__link {
  font-size: .78rem; font-weight: 600; padding: 6px 11px; border-radius: 6px;
  color: var(--text-2); white-space: nowrap; transition: background .15s, color .15s;
}
.sl-nav__link:hover { background: var(--surface); color: var(--text); }
.sl-nav__right {
  display: flex; align-items: center; gap: 8px; margin-left: 12px; flex-shrink: 0;
}
.sl-theme-toggle {
  background: var(--surface); border: 1px solid var(--border);
  color: var(--text-2); width: 34px; height: 34px; border-radius: 8px;
  font-size: 1rem; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background .15s, color .15s;
}
.sl-theme-toggle:hover { background: var(--surface-2); color: var(--text); }
.sl-ham {
  display: none; background: var(--surface); border: 1px solid var(--border);
  color: var(--text); width: 34px; height: 34px; border-radius: 8px;
  flex-direction: column; align-items: center; justify-content: center;
  gap: 5px; padding: 0; cursor: pointer; flex-shrink: 0;
}
.sl-ham .bar {
  width: 18px; height: 2px; background: currentColor;
  border-radius: 2px; transition: transform .25s, opacity .2s;
}
.sl-ham.open .bar:nth-child(1) { transform: translateY(7px) rotate(45deg); }
.sl-ham.open .bar:nth-child(2) { opacity: 0; }
.sl-ham.open .bar:nth-child(3) { transform: translateY(-7px) rotate(-45deg); }
@media(max-width:768px) {
  .sl-ham { display: flex; }
  .sl-nav__links {
    display: none; flex-direction: column; gap: 4px;
    position: absolute; top: 58px; left: 0; right: 0;
    background: var(--bg); border-bottom: 1px solid var(--border);
    padding: 12px 16px; z-index: 999;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
  }
  .sl-nav__links.open { display: flex; }
  .sl-nav__link { padding: 10px 14px; font-size: .85rem; border-radius: 8px; }
}
/* ═══ ARTICLE ═══ */
.sl-post-wrap { max-width: 760px; margin: 40px auto; padding: 0 24px 60px; }
@media(max-width:600px) { .sl-post-wrap { padding: 0 16px 40px; margin-top: 24px; } }
.sl-breadcrumb {
  font-size: .75rem; color: var(--text-3); margin-bottom: 24px;
  display: flex; align-items: center; gap: 6px;
}
.sl-breadcrumb a { color: var(--accent); }
.sl-post-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px; }
.sl-post-tag {
  font-size: .68rem; font-weight: 700; padding: 4px 10px; border-radius: 5px;
  background: var(--bg-3); color: var(--text-3);
  letter-spacing: .05em; text-transform: uppercase;
}
.sl-post-title {
  font-family: var(--font-display);
  font-size: clamp(1.8rem, 4vw, 2.6rem);
  font-weight: 900; line-height: 1.2; letter-spacing: -.02em;
  color: var(--text); margin-bottom: 16px;
}
.sl-post-meta {
  font-size: .8rem; color: var(--text-3); margin-bottom: 32px;
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
}
.sl-post-meta .dot { color: var(--border-2); }
.sl-post-img {
  width: 100%; aspect-ratio: 16/9; object-fit: cover;
  border-radius: var(--radius); margin-bottom: 8px;
}
.sl-post-credit {
  font-size: .7rem; color: var(--text-3); margin-bottom: 36px; text-align: right;
}
.sl-post-credit a { color: var(--text-3); text-decoration: underline; }
.sl-post-body { font-size: 1.05rem; line-height: 1.8; color: var(--text-2); }
.sl-post-body h2 {
  font-family: var(--font-display); font-size: 1.55rem; font-weight: 800;
  color: var(--text); margin: 2.4em 0 .6em; line-height: 1.25;
  padding-bottom: .4em; border-bottom: 1px solid var(--border);
}
.sl-post-body h3 {
  font-family: var(--font-display); font-size: 1.2rem; font-weight: 700;
  color: var(--text); margin: 1.8em 0 .5em; line-height: 1.3;
}
.sl-post-body p  { margin-bottom: 1.2em; }
.sl-post-body ul, .sl-post-body ol { margin: 0 0 1.2em 1.4em; }
.sl-post-body li { margin-bottom: .45em; }
.sl-post-body strong { color: var(--text); font-weight: 700; }
.sl-post-body blockquote {
  border-left: 3px solid var(--accent); margin: 1.8em 0; padding: 14px 20px;
  background: var(--surface); border-radius: 0 var(--radius) var(--radius) 0;
  font-style: italic; color: var(--text-2);
}
.sl-post-body a { color: var(--accent); text-decoration: underline; text-decoration-color: rgba(99,102,241,.35); }
.sl-post-body a:hover { text-decoration-color: var(--accent); }
.sl-post-divider { border: none; border-top: 1px solid var(--border); margin: 2.5em 0; }
.sl-post-footer {
  display: flex; justify-content: space-between; align-items: center;
  flex-wrap: wrap; gap: 12px; padding-top: 20px;
}
.sl-back-link {
  font-size: .82rem; font-weight: 600; color: var(--accent);
  display: inline-flex; align-items: center; gap: 6px;
  border: 1px solid rgba(99,102,241,.3); padding: 8px 16px;
  border-radius: 8px; transition: background .15s;
}
.sl-back-link:hover { background: var(--accent-glow); }
/* ═══ SHARE ═══ */
.sl-share { margin: 2.5rem 0 1.5rem; padding-top: 2rem; border-top: 1px solid var(--border); }
.sl-share-label {
  font-size: .72rem; text-transform: uppercase; letter-spacing: .1em;
  color: var(--text-3); margin-bottom: 12px; font-weight: 700;
}
.sl-share-btns { display: flex; flex-wrap: wrap; gap: 8px; }
.sl-share-btn {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 8px 14px; border-radius: 7px; font-size: .82rem;
  font-weight: 600; text-decoration: none; cursor: pointer;
  border: none; font-family: inherit; transition: opacity .15s, transform .12s;
}
.sl-share-btn:hover { opacity: .85; transform: translateY(-1px); }
.sl-share-x        { background: #000; color: #fff; }
.sl-share-linkedin { background: #0a66c2; color: #fff; }
.sl-share-facebook { background: #1877f2; color: #fff; }
.sl-share-copy     { background: var(--surface-2); color: var(--text); border: 1px solid var(--border); }
/* ═══ FOOTER ═══ */
.sl-footer { border-top: 1px solid var(--border); padding: 32px 24px; background: var(--bg-2); }
.sl-footer__inner {
  max-width: 1200px; margin: 0 auto;
  display: flex; justify-content: space-between; align-items: flex-start;
  flex-wrap: wrap; gap: 20px;
}
.sl-footer__brand { font-family: var(--font-display); font-size: 1.4rem; font-weight: 900; }
.sl-footer__brand span { color: var(--accent); }
.sl-footer__tagline { font-size: .75rem; color: var(--text-3); margin-top: 4px; }
.sl-footer__links { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 4px; }
.sl-footer__links a {
  font-size: .75rem; color: var(--text-2); padding: 4px 8px;
  border-radius: 5px; transition: background .15s;
}
.sl-footer__links a:hover { background: var(--surface); color: var(--text); }
.sl-footer__copy {
  width: 100%; font-size: .72rem; color: var(--text-3);
  border-top: 1px solid var(--border); padding-top: 14px; margin-top: 8px;
}
"""

_POST_SCRIPTS = """
  <script>
    (function(){
      var t=localStorage.getItem('sl-theme');
      if(!t) t=window.matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light';
      document.documentElement.setAttribute('data-theme',t);
    })();
    document.getElementById('themeToggle').addEventListener('click',function(){
      var next=document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark';
      document.documentElement.setAttribute('data-theme',next);
      localStorage.setItem('sl-theme',next);
    });
    var hamBtn=document.getElementById('hamBtn');
    var navLinks=document.getElementById('navLinks');
    if(hamBtn&&navLinks){
      hamBtn.addEventListener('click',function(){
        var open=navLinks.classList.toggle('open');
        hamBtn.classList.toggle('open',open);
        hamBtn.setAttribute('aria-expanded',String(open));
      });
      navLinks.querySelectorAll('.sl-nav__link').forEach(function(l){
        l.addEventListener('click',function(){
          navLinks.classList.remove('open');
          hamBtn.classList.remove('open');
          hamBtn.setAttribute('aria-expanded','false');
        });
      });
      document.addEventListener('click',function(e){
        if(!hamBtn.contains(e.target)&&!navLinks.contains(e.target)){
          navLinks.classList.remove('open');
          hamBtn.classList.remove('open');
          hamBtn.setAttribute('aria-expanded','false');
        }
      });
    }
  </script>
"""


def build_post_html(post, img_url, img_credit, og_image_url, date_str):
    tags_html    = "".join(f'<span class="sl-post-tag">{t}</span>' for t in post["tags"])
    date_nice    = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")
    year         = datetime.now().year
    post_url     = f"{SITE_URL}/posts/{date_str}-{post['slug']}.html"
    title_enc    = requests.utils.quote(post["title"])
    url_enc      = requests.utils.quote(post_url)
    reading_time = post.get("reading_time", "5 min read")
    first_tag    = post["tags"][0] if post.get("tags") else "Article"

    json_ld = json.dumps({
        "@context":         "https://schema.org",
        "@type":            "Article",
        "headline":         post["title"],
        "description":      post["meta_description"],
        "image":            og_image_url,
        "datePublished":    date_str,
        "dateModified":     date_str,
        "author":           {"@type": "Person", "name": "Sujit Luintel", "url": "https://sluintel.com.np"},
        "publisher":        {"@type": "Organization", "name": "Sujit Luintel",
                             "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/favicon.ico"}},
        "mainEntityOfPage": {"@type": "WebPage", "@id": post_url},
        "keywords":         ", ".join(post.get("tags", [])),
    }, ensure_ascii=False, indent=2)

    share_buttons = f"""
  <div class="sl-share">
    <div class="sl-share-label">Share this post</div>
    <div class="sl-share-btns">
      <a class="sl-share-btn sl-share-x"
         href="https://twitter.com/intent/tweet?text={title_enc}&url={url_enc}"
         target="_blank" rel="noopener" aria-label="Share on X">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.742l7.732-8.855L2.25 2.25h6.918l4.274 5.648 5.802-5.648Zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
        </svg>X
      </a>
      <a class="sl-share-btn sl-share-linkedin"
         href="https://www.linkedin.com/shareArticle?mini=true&url={url_enc}&title={title_enc}"
         target="_blank" rel="noopener" aria-label="Share on LinkedIn">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
        </svg>LinkedIn
      </a>
      <a class="sl-share-btn sl-share-facebook"
         href="https://www.facebook.com/sharer/sharer.php?u={url_enc}"
         target="_blank" rel="noopener" aria-label="Share on Facebook">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
        </svg>Facebook
      </a>
      <button class="sl-share-btn sl-share-copy" onclick="(function(){{
        navigator.clipboard.writeText('{post_url}').then(function(){{
          var el=document.getElementById('sl-copy-lbl');
          el.textContent='Copied!';
          setTimeout(function(){{el.textContent='Copy Link';}},2000);
        }});
      }})()" aria-label="Copy link">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="9" y="9" width="13" height="13" rx="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
        <span id="sl-copy-lbl">Copy Link</span>
      </button>
    </div>
  </div>"""

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <script>(function(){{var t=localStorage.getItem('sl-theme');if(!t)t=window.matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light';document.documentElement.setAttribute('data-theme',t);}})();</script>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{post['title']} — Sujit Luintel</title>
  <meta name="description"           content="{post['meta_description']}"/>
  <meta property="og:title"          content="{post['title']}"/>
  <meta property="og:description"    content="{post['meta_description']}"/>
  <meta property="og:image"          content="{og_image_url}"/>
  <meta property="og:image:width"    content="1200"/>
  <meta property="og:image:height"   content="630"/>
  <meta property="og:type"           content="article"/>
  <meta property="og:url"            content="{post_url}"/>
  <meta name="twitter:card"          content="summary_large_image"/>
  <meta name="twitter:title"         content="{post['title']}"/>
  <meta name="twitter:description"   content="{post['meta_description']}"/>
  <meta name="twitter:image"         content="{og_image_url}"/>
  <link rel="canonical" href="{post_url}"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-WJEQKLB827"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-WJEQKLB827');</script>
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2480859517203371" crossorigin="anonymous"></script>
  <script type="application/ld+json">{json_ld}</script>
  <style>{_POST_CSS}</style>
</head>
<body>

  <nav class="sl-nav" role="navigation" aria-label="Main navigation">
    <div class="sl-nav__inner">
      <a href="/" class="sl-nav__brand">Sujit <span>Luintel</span></a>
      <div class="sl-nav__links" id="navLinks">
        <a href="/category/trending"      class="sl-nav__link">🔥 Trending</a>
        <a href="/category/ai-automation" class="sl-nav__link">🤖 AI</a>
        <a href="/category/sports"        class="sl-nav__link">⚽ Sports</a>
        <a href="/category/finance"       class="sl-nav__link">💰 Finance</a>
        <a href="/category/entertainment" class="sl-nav__link">🎬 Entertainment</a>
        <a href="/category/technology"    class="sl-nav__link">💻 Tech</a>
        <a href="/category/deep-dives"    class="sl-nav__link">🔍 Deep Dives</a>
        <a href="/category/all"           class="sl-nav__link">📰 All Posts</a>
        <a href="/#about"                 class="sl-nav__link">About</a>
      </div>
      <div class="sl-nav__right">
        <button class="sl-ham" id="hamBtn" aria-label="Toggle menu" aria-expanded="false">
          <span class="bar"></span><span class="bar"></span><span class="bar"></span>
        </button>
        <button class="sl-theme-toggle" id="themeToggle" aria-label="Toggle theme">◐</button>
      </div>
    </div>
  </nav>

  <div class="sl-post-wrap">
    <div class="sl-breadcrumb">
      <a href="/">Home</a> <span>›</span> <span>{first_tag}</span>
    </div>
    <div class="sl-post-tags">{tags_html}</div>
    <h1 class="sl-post-title">{post['title']}</h1>
    <div class="sl-post-meta">
      <span>📅 {date_nice}</span>
      <span class="dot">·</span>
      <span>⏱ {reading_time}</span>
      <span class="dot">·</span>
      <span>✍️ Sujit Luintel</span>
    </div>
    <img class="sl-post-img" src="{img_url}" alt="{post['title']}" loading="eager"/>
    <p class="sl-post-credit">{img_credit}</p>
    <ins class="adsbygoogle" style="display:block;margin-bottom:28px"
         data-ad-client="ca-pub-2480859517203371" data-ad-slot="auto"
         data-ad-format="auto" data-full-width-responsive="true"></ins>
    <script>(adsbygoogle=window.adsbygoogle||[]).push({{}});</script>
    <div class="sl-post-body">
      {post['content_html']}
    </div>
    <hr class="sl-post-divider"/>
    {share_buttons}
    <div class="sl-post-footer">
      <div class="sl-post-tags">{tags_html}</div>
      <a href="/" class="sl-back-link">← Back to Home</a>
    </div>
  </div>

  <footer class="sl-footer">
    <div class="sl-footer__inner">
      <div>
        <div class="sl-footer__brand">Sujit <span>Luintel</span></div>
        <div class="sl-footer__tagline">AI-powered daily blog by Sujit Luintel · Kathmandu, Nepal</div>
        <nav class="sl-footer__links" aria-label="Footer links">
          <a href="/category/ai-automation">🤖 AI</a>
          <a href="/category/sports">⚽ Sports</a>
          <a href="/category/finance">💰 Finance</a>
          <a href="/category/entertainment">🎬 Entertainment</a>
          <a href="/category/technology">💻 Tech</a>
          <a href="/category/trending">🔥 Trending</a>
        </nav>
      </div>
      <p class="sl-footer__copy">© {year} Sujit Luintel · Content generated with AI · Auto-published via GitHub Actions</p>
    </div>
  </footer>

{_POST_SCRIPTS}
</body>
</html>"""


# ─────────────────────────────────────────
# 7. UPDATE posts.json
# ─────────────────────────────────────────
def load_posts():
    if POSTS_JSON.exists():
        try:
            content = POSTS_JSON.read_text().strip()
            if content:
                return json.loads(content)
        except (json.JSONDecodeError, ValueError):
            print("posts.json was malformed — starting fresh")
    return []


def update_posts_json(post, img_url, date_str):
    posts    = load_posts()
    filename = f"{date_str}-{post['slug']}.html"
    entry    = {
        "title":            post["title"],
        "slug":             post["slug"],
        "date":             date_str,
        "meta_description": post["meta_description"],
        "tags":             post["tags"],
        "image_url":        img_url,
        "reading_time":     post.get("reading_time", "5 min read"),
        "url":              f"posts/{filename}",
        "keyword":          post.get("keyword", ""),
    }
    posts.insert(0, entry)
    POSTS_JSON.write_text(json.dumps(posts, indent=2))
    print(f"posts.json updated  ({len(posts)} posts total)")
    return posts, filename


# ─────────────────────────────────────────
# 8. UPDATE posts-data.json (feeds homepage JS)
# ─────────────────────────────────────────
def update_posts_data_json(posts):
    """Write assets/js/posts-data.json — read by the homepage JS."""
    POSTS_DATA_JSON.parent.mkdir(parents=True, exist_ok=True)
    data = []
    for p in posts:
        word_count = len(p.get("meta_description", "").split()) * 8
        data.append({
            "url":       p.get("url", ""),
            "title":     p.get("title", ""),
            "date":      p.get("date", ""),
            "image":     p.get("image_url", ""),
            "tags":      p.get("tags", []),
            "excerpt":   p.get("meta_description", ""),
            "wordCount": word_count,
        })
    POSTS_DATA_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"posts-data.json updated ({len(data)} posts) → assets/js/posts-data.json")


# ─────────────────────────────────────────
# 9. REGENERATE sitemap.xml
# ─────────────────────────────────────────
def build_sitemap(posts):
    now_iso  = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    # ── Category pages to include ──────────────────────────────────────────
    CATEGORY_SLUGS = [
        "trending", "ai-automation", "sports", "finance",
        "entertainment", "technology", "deep-dives", "all",
    ]

    # ── Deduplicate posts by URL (posts.json can have duplicate slugs) ─────
    seen_urls = set()
    unique_posts = []
    for p in posts:
        url = p.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_posts.append(p)

    # ── Build XML manually as a string (avoids minidom BOM/encoding bugs) ──
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
        '        xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9',
        '          http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">',
    ]

    def add_url(loc, lastmod, changefreq, priority):
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append(f"    <changefreq>{changefreq}</changefreq>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append("  </url>")

    # Homepage
    add_url(f"{SITE_URL}/", now_iso, "daily", "1.00")

    # Category pages
    for slug in CATEGORY_SLUGS:
        add_url(f"{SITE_URL}/category/{slug}", now_iso, "daily", "0.90")

    # Individual posts — use actual post date for lastmod
    for p in unique_posts:
        date_str = p.get("date", "")
        if date_str:
            try:
                lastmod = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%dT00:00:00+00:00")
            except ValueError:
                lastmod = now_iso
        else:
            lastmod = now_iso
        add_url(f"{SITE_URL}/{p['url']}", lastmod, "weekly", "0.80")

    lines.append("</urlset>")

    sitemap_content = "\n".join(lines) + "\n"

    # Write without BOM — plain UTF-8 text
    SITEMAP_PATH.write_text(sitemap_content, encoding="utf-8")
    print(f"sitemap.xml updated ({len(unique_posts)} unique posts + 1 homepage + {len(CATEGORY_SLUGS)} category pages)")
    if len(unique_posts) < len(posts):
        print(f"  ↳ Removed {len(posts) - len(unique_posts)} duplicate URLs from sitemap")


# ─────────────────────────────────────────
# 10. REGENERATE llms.txt
# ─────────────────────────────────────────
def build_llms_txt(posts):
    today      = datetime.now().strftime("%Y-%m-%d")
    total      = len(posts)
    latest     = posts[0]["title"] if posts else "Coming soon"
    latest_url = f"{SITE_URL}/{posts[0]['url']}" if posts else ""
    recent_lines = ""
    for p in posts[:10]:
        tags = ", ".join(p.get("tags", [])[:3])
        recent_lines += f"- [{p['title']}]({SITE_URL}/{p['url']}) — {p['date']} — {tags}\n"

    content = f"""# Sujit Luintel's AI & Automation Blog | by Sujit Luintel

> This is the automated AI research and insights blog by Sujit Luintel — digital strategist, author, and digital marketing expert from Kathmandu, Nepal.

## Identity
Blog Name: Sujit Luintel AI Blog
Owner & Creator: Sujit Luintel
Author Website: https://sluintel.com.np
Blog URL: {SITE_URL}
Location: Kathmandu, Nepal
Publishing Frequency: Daily (fully automated)
Total Posts Published: {total}
Last Updated: {today}
Latest Post: {latest}
Latest Post URL: {latest_url}
Primary Niche: AI Tools, Marketing Automation, Digital Strategy, SEO

## About This Blog
This blog is built and owned by Sujit Luintel, a leading digital strategist and digital marketing expert in Nepal.

## Topics Covered
AI Tools, Marketing Automation, SEO, No-Code Automation, Workflow Automation, Generative AI, LLMs, AI Writing Tools, AI SEO, Content Automation, Digital Strategy, Productivity, Business Efficiency, AI Agents, Prompt Engineering

## Recent Posts
{recent_lines}
## Blog Structure
- Homepage: {SITE_URL}/
- Sitemap: {SITE_URL}/sitemap.xml
- Posts directory: {SITE_URL}/posts/

## Technology Stack
- Content Generation: Gemini AI (Google)
- Trend Discovery: Google Trends RSS Feed
- Images: Pexels, Openverse, Unsplash
- OG Images: Generated with Pillow at build time
- Hosting: GitHub Pages
- Automation: GitHub Actions (daily at Nepal morning time)
- Built by: Sujit Luintel

## Contact & Author
Author: Sujit Luintel
Primary Web Presence: https://sluintel.com.np
AI Blog: {SITE_URL}
Location: Kathmandu, Nepal
"""
    LLMS_PATH.write_text(content.strip(), encoding="utf-8")
    print(f"llms.txt updated ({total} posts)")


# ─────────────────────────────────────────
# 11. GENERATE RSS FEED (feed.xml)
# ─────────────────────────────────────────
def build_rss_feed(posts):
    now_rfc = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    def _item(p):
        pub = datetime.strptime(p["date"], "%Y-%m-%d").strftime("%a, %d %b %Y 00:00:00 +0000")
        url = f"{SITE_URL}/{p['url']}"
        cats = "".join(f"    <category>{t}</category>\n" for t in p.get("tags", []))
        return (
            f"  <item>\n"
            f"    <title><![CDATA[{p['title']}]]></title>\n"
            f"    <link>{url}</link>\n"
            f"    <guid isPermaLink=\"true\">{url}</guid>\n"
            f"    <pubDate>{pub}</pubDate>\n"
            f"    <description><![CDATA[{p['meta_description']}]]></description>\n"
            f"    <enclosure url=\"{p['image_url']}\" type=\"image/jpeg\" length=\"0\"/>\n"
            f"{cats}"
            f"  </item>"
        )

    items = "\n".join(_item(p) for p in posts[:20])
    rss = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        '<channel>\n'
        f'  <title>Sujit Luintel — AI Tools &amp; Automation</title>\n'
        f'  <link>{SITE_URL}/</link>\n'
        f'  <description>Daily AI tools and automation insights, auto-published every day.</description>\n'
        f'  <language>en-us</language>\n'
        f'  <lastBuildDate>{now_rfc}</lastBuildDate>\n'
        f'  <atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>\n'
        f'  <image>\n'
        f'    <url>{SITE_URL}/favicon.ico</url>\n'
        f'    <title>Sujit Luintel</title>\n'
        f'    <link>{SITE_URL}/</link>\n'
        f'  </image>\n'
        f'{items}\n'
        '</channel>\n'
        '</rss>'
    )
    RSS_PATH.write_text(rss, encoding="utf-8")
    print(f"feed.xml updated ({min(len(posts), 20)} items)")


# ─────────────────────────────────────────
# 12. REGENERATE robots.txt
# ─────────────────────────────────────────
def build_robots_txt():
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )
    ROBOTS_PATH.write_text(content, encoding="utf-8")
    print("robots.txt updated")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Sujit Luintel Auto Blog Generator")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Generate and validate everything but write NO files"
    )
    args = parser.parse_args()
    dry  = args.dry_run

    if dry:
        print("\n DRY RUN — no files will be written\n")
    else:
        print("\n Auto Blog Generator starting…\n")

    start = time.time()

    POSTS_DIR.mkdir(exist_ok=True)
    OG_DIR.mkdir(parents=True, exist_ok=True)

    try:
        keyword      = get_trending_keyword()
        post         = generate_blog_post(keyword)
        date_str     = datetime.now().strftime("%Y-%m-%d")
        post["slug"] = _unique_slug(post["slug"], date_str)
        img_url, img_credit = get_feature_image(keyword)
        og_image_url = generate_og_image(post["title"], post["slug"])
        post_html    = build_post_html(post, img_url, img_credit, og_image_url, date_str)
        filename     = f"{date_str}-{post['slug']}.html"

        if dry:
            print(f"\n DRY RUN complete — would have written: posts/{filename}")
            print(f"   Title : {post['title']}")
            print(f"   Slug  : {post['slug']}")
            print(f"   Image : {img_url[:60]}…")
            print(f"\n⏱  Finished in {time.time()-start:.1f}s (dry run)\n")
            return

        (POSTS_DIR / filename).write_text(post_html, encoding="utf-8")
        print(f" Post written → posts/{filename}")

        posts, _ = update_posts_json(post, img_url, date_str)
        update_posts_data_json(posts)

        build_sitemap(posts)
        build_rss_feed(posts)
        build_llms_txt(posts)
        build_robots_txt()

        print(f"\n Done in {time.time()-start:.1f}s — '{post['title']}' is live at posts/{filename}\n")

    except KeyboardInterrupt:
        print("\n Interrupted by user")
        sys.exit(0)
    except Exception as exc:
        print(f"\n Fatal error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
