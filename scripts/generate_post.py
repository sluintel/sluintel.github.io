#!/usr/bin/env python3
"""
Sujit Luintel Auto Blog Generator
Niche: AI Tools & Automation
Runs daily via GitHub Actions
"""

import os
import io
import json
import re
import random
import textwrap
import requests
import xml.etree.ElementTree as ET
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
USED_KW_FILE = REPO_ROOT / "used_keywords.json"
INDEX_HTML   = REPO_ROOT / "index.html"
SITEMAP_PATH = REPO_ROOT / "sitemap.xml"
LLMS_PATH    = REPO_ROOT / "llms.txt"

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

# Dynamic title templates
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
            print("⚠️  used_keywords.json was malformed — resetting it")
    return []


def save_used_keyword(kw):
    used = load_used_keywords()
    used.append(kw)
    USED_KW_FILE.write_text(json.dumps(used[-80:], indent=2))


def _is_ai_tech(text: str) -> bool:
    words = set(re.findall(r"[a-z0-9]+", text.lower()))
    return bool(words & AI_TECH_TERMS)


def clean_topic(title: str) -> str:
    """
    Clean unnecessary formatting from trend titles.
    """
    title = re.sub(r"\b(2024|2025|2026)\b", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def detect_category(keyword: str) -> str:
    """
    Detect category of trend.
    """
    text = keyword.lower()

    if any(word in text for word in AI_TECH_TERMS):
        return "tech"

    if any(word in text for word in SPORTS_KEYWORDS):
        return "sports"

    if any(word in text for word in ENTERTAINMENT_KEYWORDS):
        return "entertainment"

    return "general"


def generate_dynamic_title(keyword: str) -> str:
    """
    Generate natural SEO-friendly titles.
    """
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

    # Safety cleanup
    title = re.sub(r"\s+", " ", title).strip()

    return title


def fetch_trends_rss(geo: str, url: str) -> list:
    try:
        resp = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; SluIntelBot/1.0; +https://sluintel.github.io)"
            },
            timeout=15,
        )

        if resp.status_code != 200:
            print(f"⚠️  Trends RSS ({geo}): HTTP {resp.status_code}")
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
        print(f"⚠️  Trends RSS ({geo}): XML parse error — {e}")
        return []

    except requests.RequestException as e:
        print(f"⚠️  Trends RSS ({geo}): request error — {e}")
        return []


def get_trending_keyword() -> str:
    all_titles = []

    for geo, url in TRENDS_RSS_FEEDS:
        titles = fetch_trends_rss(geo, url)

        # PRIORITY 1 → AI / TECH
        for title in titles:
            if _is_ai_tech(title):
                print(f"✅ Trending AI/Tech RSS ({geo}): {title}")
                save_used_keyword(title)
                return title

        # Save all trends for smart reframing
        for title in titles:
            all_titles.append((geo, title))

    # PRIORITY 2 → Reframe non-tech trends naturally
    if all_titles:
        geo, title = random.choice(all_titles[:10])

        reframed = generate_dynamic_title(title)

        print(f"✅ Reframed trending topic ({geo}): {reframed}")

        save_used_keyword(reframed)

        return reframed

    # PRIORITY 3 → fallback keyword pool
    used = load_used_keywords()

    available = [k for k in FALLBACK_KEYWORDS if k not in used]

    if not available:
        print("ℹ️  All fallback keywords used — resetting pool")
        USED_KW_FILE.write_text(json.dumps([], indent=2))
        available = FALLBACK_KEYWORDS

    kw = random.choice(available)

    save_used_keyword(kw)

    print(f"✅ Fallback keyword: {kw}")

    return kw


# ─────────────────────────────────────────
# 2. INTERNAL LINKING HELPERS
# ─────────────────────────────────────────

# Tags too generic to drive meaningful relevance scoring
_STOP_TAGS = {
    "ai tools", "automation", "ai", "tools", "future of work",
    "2026 trends", "productivity", "digital transformation",
    "tech trends", "future tech", "ai automation",
}


def _tokenise(text: str) -> set:
    """Lowercase word tokens, dropping single-char noise."""
    return {w for w in re.split(r"\W+", text.lower()) if len(w) > 1}


def _build_posts_index() -> list:
    """
    Load posts.json and return a clean, deduplicated index for link scoring.
    Reuses the existing load_posts() helper — no extra file I/O.
    """
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
            "keyword": p.get("keyword", ""),   # persisted by our generator
        })
    return index


def _score_relevance(post: dict, kw_tokens: set, used_keywords: list) -> int:
    score = 0
    # Title token overlap
    score += len(kw_tokens & _tokenise(post["title"])) * 3
    # Keyword-to-keyword overlap (strongest signal)
    if post["keyword"]:
        score += len(kw_tokens & _tokenise(post["keyword"])) * 4
    # Meaningful tag overlap
    meaningful_tags = [t for t in post["tags"] if t not in _STOP_TAGS]
    score += len(kw_tokens & _tokenise(" ".join(meaningful_tags))) * 2
    # Mild boost for topical neighbours in keyword history
    for used_kw in used_keywords:
        if len(kw_tokens & _tokenise(used_kw)) >= 2:
            score += 1
    return score


def _select_link_candidates(
    posts_index: list,
    current_keyword: str,
    used_keywords: list,
    max_links: int = 6,
    min_score: int = 2,
) -> list:
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
    """Strip any <a href> that doesn't match a real post URL."""
    def _fix(match):
        href  = match.group(1).lstrip("/")
        inner = match.group(2)
        if href in valid_urls:
            return match.group(0)
        print(f"⚠️  Stripped hallucinated link: {match.group(1)}")
        return inner
    return re.sub(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>', _fix, html, flags=re.DOTALL)


# ─────────────────────────────────────────
# 3. GENERATE BLOG POST WITH GEMINI
# ─────────────────────────────────────────
def generate_blog_post(keyword: str) -> dict:
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)

    # Build internal-link context BEFORE calling Gemini
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

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )

    data = json.loads(response.text)

    # Sanitise slug
    data["slug"] = re.sub(r"[^a-z0-9\-]", "", data["slug"].lower().replace(" ", "-"))
    data["slug"] = re.sub(r"-+", "-", data["slug"]).strip("-")

    # Persist keyword so future posts can find and link back to this one
    data["keyword"] = keyword

    # Strip any links Gemini hallucinated
    if valid_urls:
        data["content_html"] = _validate_links(data["content_html"], valid_urls)

    links_found = re.findall(r'<a href=', data["content_html"])
    print(f"✅ Post generated: {data['title']}")
    print(f"   🔗 Internal links embedded: {len(links_found)}")
    return data


# ─────────────────────────────────────────
# 4. FETCH FEATURE IMAGE
# ─────────────────────────────────────────
import random
import hashlib
import requests

# ── helpers ────────────────────────────────────────────────────────────────────

def _is_ai_tech(keyword: str) -> bool:
    AI_WORDS = {"ai", "artificial", "intelligence", "machine", "learning",
                "automation", "robot", "chatgpt", "claude", "gemini", "llm",
                "neural", "deep", "model", "gpt", "generative"}
    return bool(AI_WORDS & set(keyword.lower().split()))


def _build_credit(name, profile_url, platform, platform_url):
    return (
        f'Photo by <a href="{profile_url}" target="_blank" rel="noopener">{name}</a>'
        f' on <a href="{platform_url}" target="_blank" rel="noopener">{platform}</a>'
    )


def _keyword_hash_page(keyword: str, total_pages: int = 8) -> int:
    """
    Deterministic-but-varied page offset derived from the keyword text.
    Each unique keyword maps to a different Pexels page, so repeated runs
    for the same post are stable while different posts get different images.
    """
    h = int(hashlib.md5(keyword.lower().encode()).hexdigest(), 16)
    return (h % total_pages) + 1          # pages 1-8


def _build_queries(keyword: str) -> list[str]:
    """
    Return a ranked list of progressively broader search queries.
    More specific first so we get relevant images when possible,
    broad fallbacks to avoid empty results.
    """
    words = keyword.split()

    # --- sport/match queries ---
    # e.g. "Lakers vs Thunder" → ["Lakers Thunder basketball", "Lakers Thunder", ...]
    if "vs" in keyword.lower():
        teams = [w for w in words if w.lower() != "vs" and not w.isdigit()]
        queries = [
            " ".join(teams[:2]) + " sport action",
            " ".join(teams[:2]),
            "sport action stadium crowd",
        ]
    # --- "how AI is changing X" pattern ---
    elif "how ai" in keyword.lower() or "ai is" in keyword.lower():
        # extract the subject (last 2-3 words usually)
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

    # deduplicate while preserving order
    seen, unique = set(), []
    for q in queries:
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            unique.append(q)
    return unique


# ── per-source fetchers ─────────────────────────────────────────────────────────

def _pexels(query: str, keyword: str, api_key: str):
    if not api_key:
        return None
    page = _keyword_hash_page(keyword, total_pages=8)
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            params={
                "query": query,
                "orientation": "landscape",
                "per_page": 15,          # larger pool → more variety
                "page": page,            # ← KEY FIX: different page per keyword
                "size": "large",
            },
            headers={"Authorization": api_key},
            timeout=10,
        )
        if r.status_code != 200:
            print(f"⚠️  Pexels HTTP {r.status_code} for '{query}' page {page}")
            return None
        photos = r.json().get("photos", [])
        if not photos:
            return None
        photo = random.choice(photos)
        return (
            photo["src"]["large2x"],
            _build_credit(photo["photographer"], photo["photographer_url"],
                          "Pexels", "https://www.pexels.com"),
        )
    except Exception as e:
        print(f"⚠️  Pexels error: {e}")
        return None


def _unsplash(query: str, keyword: str, api_key: str):
    if not api_key:
        return None
    page = _keyword_hash_page(keyword, total_pages=5)
    try:
        r = requests.get(
            "https://api.unsplash.com/search/photos",
            params={
                "query": query,
                "orientation": "landscape",
                "content_filter": "high",
                "per_page": 15,
                "page": page,            # ← varied page per keyword
                "order_by": "relevant",
            },
            headers={"Authorization": f"Client-ID {api_key}"},
            timeout=10,
        )
        if r.status_code != 200:
            print(f"⚠️  Unsplash HTTP {r.status_code} for '{query}' page {page}")
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
        print(f"⚠️  Unsplash error: {e}")
        return None


def _openverse(query: str, keyword: str):
    page = _keyword_hash_page(keyword, total_pages=6)
    try:
        r = requests.get(
            "https://api.openverse.org/v1/images/",
            params={
                "q": query,
                "license_type": "commercial",
                "aspect_ratio": "wide",
                "page_size": 15,
                "page": page,
                "mature": "false",
            },
            headers={"User-Agent": "SluIntelBot/1.0 (https://sluintel.github.io)"},
            timeout=10,
        )
        if r.status_code != 200:
            print(f"⚠️  Openverse HTTP {r.status_code} for '{query}' page {page}")
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
        print(f"⚠️  Openverse error: {e}")
        return None


# ── public function ─────────────────────────────────────────────────────────────

def get_feature_image(keyword: str):
    """
    Return (image_url, credit_html) for *keyword*.

    Strategy:
      1. Try Pexels with progressively broader queries (varied page per keyword)
      2. Try Openverse
      3. Try Unsplash
      4. Hard-coded fallback

    The page offset is derived from a hash of the keyword so:
      - The same keyword always gets the same page (stable re-runs)
      - Different keywords land on different pages → image variety
    """
    import os
    PEXELS_KEY   = os.environ.get("PEXELS_API_KEY", "")
    UNSPLASH_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")

    FALLBACK_IMAGES = [
        "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=1200&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=1200&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1655720031554-a929595ffad7?w=1200&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1676299081847-824916de030a?w=1200&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=1200&auto=format&fit=crop",
    ]

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
                print(f"✅ [{source_name}] Image fetched for '{query}' (keyword: '{keyword}')")
                return img_url, credit
            print(f"↩️  [{source_name}] No result for '{query}', trying next…")

    # last resort: pick a fallback seeded by keyword so different posts
    # at least get different fallback images
    idx    = _keyword_hash_page(keyword, total_pages=len(FALLBACK_IMAGES)) - 1
    img    = FALLBACK_IMAGES[idx]
    credit = 'Photo from <a href="https://unsplash.com" target="_blank" rel="noopener">Unsplash</a>'
    print("⚠️  All sources failed — using hardcoded fallback image")
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
    print(f"✅ OG image saved → posts/og/{slug}.png")
    return og_url


# ─────────────────────────────────────────
# 6. BUILD POST HTML FILE
# ─────────────────────────────────────────
def build_post_html(post, img_url, img_credit, og_image_url, date_str):
    tags_html = "".join(f'<span class="tag">{t}</span>' for t in post["tags"])
    date_nice = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")
    year      = datetime.now().year
    post_url  = f"{SITE_URL}/posts/{date_str}-{post['slug']}.html"
    title_enc = requests.utils.quote(post["title"])
    url_enc   = requests.utils.quote(post_url)

    share_buttons = f"""
      <div class="share-section">
        <p class="share-label">Share this post</p>
        <div class="share-buttons">
          <a class="share-btn share-x"
             href="https://twitter.com/intent/tweet?text={title_enc}&url={url_enc}"
             target="_blank" rel="noopener" aria-label="Share on X">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.742l7.732-8.855L2.25 2.25h6.918l4.274 5.648 5.802-5.648Zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
            </svg>
            Share on X
          </a>
          <a class="share-btn share-linkedin"
             href="https://www.linkedin.com/shareArticle?mini=true&url={url_enc}&title={title_enc}"
             target="_blank" rel="noopener" aria-label="Share on LinkedIn">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
            </svg>
            LinkedIn
          </a>
          <a class="share-btn share-facebook"
             href="https://www.facebook.com/sharer/sharer.php?u={url_enc}"
             target="_blank" rel="noopener" aria-label="Share on Facebook">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
            </svg>
            Facebook
          </a>
          <button class="share-btn share-copy" onclick="copyLink()" aria-label="Copy link">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
            <span id="copy-label">Copy Link</span>
          </button>
        </div>
      </div>
      <script>
        function copyLink() {{
          navigator.clipboard.writeText("{post_url}").then(function() {{
            var el = document.getElementById("copy-label");
            el.textContent = "Copied!";
            setTimeout(function() {{ el.textContent = "Copy Link"; }}, 2000);
          }});
        }}
      </script>"""

    share_css = """
      <style>
        .share-section {
          margin: 2.5rem 0 1.5rem;
          padding-top: 2rem;
          border-top: 1px solid rgba(255,255,255,0.08);
        }
        .share-label {
          font-size: .8rem;
          text-transform: uppercase;
          letter-spacing: .1em;
          color: #888;
          margin-bottom: .75rem;
        }
        .share-buttons { display: flex; flex-wrap: wrap; gap: .6rem; }
        .share-btn {
          display: inline-flex;
          align-items: center;
          gap: .45rem;
          padding: .5rem 1rem;
          border-radius: 6px;
          font-size: .85rem;
          font-weight: 500;
          text-decoration: none;
          cursor: pointer;
          border: none;
          transition: opacity .15s, transform .1s;
        }
        .share-btn:hover { opacity: .85; transform: translateY(-1px); }
        .share-x        { background: #000; color: #fff; }
        .share-linkedin { background: #0a66c2; color: #fff; }
        .share-facebook { background: #1877f2; color: #fff; }
        .share-copy     { background: #374151; color: #fff; }
      </style>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-WJEQKLB827"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-WJEQKLB827');
  </script>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{post['title']} | Sujit Luintel</title>
  <meta name="description" content="{post['meta_description']}"/>
  <meta property="og:title"       content="{post['title']}"/>
  <meta property="og:description" content="{post['meta_description']}"/>
  <meta property="og:image"       content="{og_image_url}"/>
  <meta property="og:image:width"  content="1200"/>
  <meta property="og:image:height" content="630"/>
  <meta property="og:type"        content="article"/>
  <meta property="og:url"         content="{post_url}"/>
  <meta name="twitter:card"        content="summary_large_image"/>
  <meta name="twitter:title"       content="{post['title']}"/>
  <meta name="twitter:description" content="{post['meta_description']}"/>
  <meta name="twitter:image"       content="{og_image_url}"/>
  <link rel="stylesheet" href="../style.css"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet"/>
  {share_css}
</head>
<body>
  <header class="site-header">
    <nav class="nav-container">
      <a href="/" class="logo">Sujit<span>Luintel</span></a>
      <div class="nav-links">
        <a href="/">Home</a>
        <a href="/#about">About</a>
      </div>
    </nav>
  </header>
  <main class="post-main">
    <article class="post-article">
      <div class="post-header">
        <div class="post-meta-top">{tags_html}</div>
        <h1 class="post-title">{post['title']}</h1>
        <div class="post-meta">
          <span>📅 {date_nice}</span>
          <span class="dot">·</span>
          <span>⏱ {post.get('reading_time', '5 min read')}</span>
        </div>
      </div>
      <div class="post-feature-image">
        <img src="{img_url}" alt="{post['title']}" loading="lazy"/>
        <p class="image-credit">{img_credit}</p>
      </div>
      <div class="post-content">
        {post['content_html']}
      </div>
      {share_buttons}
      <div class="post-footer">
        <div class="post-tags"><strong>Tags:</strong> {tags_html}</div>
        <a href="/" class="back-link">← Back to Home</a>
      </div>
    </article>
  </main>
  <footer class="site-footer">
    <p>© {year} Sujit Luintel · AI Tools &amp; Automation Insights</p>
    <p style="margin-top:.25rem;">Auto-published with AI · Powered by Gemini &amp; GitHub Actions</p>
  </footer>
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
            print("⚠️  posts.json was malformed — starting fresh")
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
        # ← NEW: persisted so future posts can find and link back to this one
        "keyword":          post.get("keyword", ""),
    }
    posts.insert(0, entry)
    POSTS_JSON.write_text(json.dumps(posts, indent=2))
    print(f"✅ posts.json updated  ({len(posts)} posts total)")
    return posts, filename


# ─────────────────────────────────────────
# 8. REGENERATE index.html
# ─────────────────────────────────────────
def build_index_html(posts):
    cards = ""
    for i, p in enumerate(posts):
        featured  = " featured-card" if i == 0 else ""
        tags_html = "".join(f'<span class="tag">{t}</span>' for t in p["tags"][:2])
        cards += f"""
      <article class="post-card{featured}">
        <a href="{p['url']}" class="card-img-link">
          <div class="card-image" style="background-image:url('{p['image_url']}')"></div>
        </a>
        <div class="card-body">
          <div class="card-tags">{tags_html}</div>
          <h2 class="card-title"><a href="{p['url']}">{p['title']}</a></h2>
          <p class="card-excerpt">{p['meta_description']}</p>
          <div class="card-meta">
            <span>{p['date']}</span><span class="dot">·</span>
            <span>{p.get('reading_time', '5 min read')}</span>
          </div>
        </div>
      </article>"""

    grid_inner = cards if cards else '<p class="no-posts">First post is being generated…</p>'
    year  = datetime.now().year
    total = len(posts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-WJEQKLB827"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-WJEQKLB827');
  </script>
  <meta name="google-site-verification" content="JQTOXeyvg5ypfjq2nyjXH_H0OXcKh3QdcYPPrbh7mh4" />
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Sujit Luintel — AI Tools &amp; Automation Insights</title>
  <meta name="description" content="Daily insights on AI tools, automation software, and the future of intelligent workflows. Stay ahead with Sujit Luintel."/>
  <meta property="og:title" content="Sujit Luintel — AI Tools &amp; Automation"/>
  <meta property="og:description" content="Daily AI tools and automation insights, auto-published every day."/>
  <link rel="stylesheet" href="style.css"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet"/>
</head>
<body>
  <header class="site-header">
    <nav class="nav-container">
      <a href="/" class="logo">Sujit<span>Luintel</span></a>
      <div class="nav-links">
        <a href="#latest">Latest</a>
        <a href="#about">About</a>
      </div>
    </nav>
  </header>
  <section class="hero">
    <div class="hero-content">
      <div class="hero-badge">🤖 Fully Automated AI Blog</div>
      <h1>AI Tools &amp; Automation<br/><span class="gradient-text">Insights That Matter</span></h1>
      <p>Daily deep-dives on AI tools, automation workflows, and intelligent software — auto-curated, auto-written, always fresh.</p>
      <div class="hero-stats">
        <div class="stat"><strong>{total}</strong><span>Articles</span></div>
        <div class="stat"><strong>Daily</strong><span>Updates</span></div>
        <div class="stat"><strong>100%</strong><span>Automated</span></div>
      </div>
    </div>
    <div class="hero-visual">
      <div class="terminal">
        <div class="terminal-bar"><span></span><span></span><span></span></div>
        <div class="terminal-body">
          <p><span class="t-green">✓</span> Fetching trending keywords…</p>
          <p><span class="t-green">✓</span> Generating blog post with AI…</p>
          <p><span class="t-green">✓</span> Fetching royalty-free image…</p>
          <p><span class="t-cyan">→</span> Publishing to sluintel.github.io</p>
          <p><span class="t-cyan">→</span> Learning new things daily · Sujit Luintel</p>
          <p class="t-blink">_</p>
        </div>
      </div>
    </div>
  </section>
  <section class="posts-section" id="latest">
    <div class="section-header">
      <h2>Latest Posts</h2>
      <span class="badge">Auto-published daily</span>
    </div>
    <div class="posts-grid">
      {grid_inner}
    </div>
  </section>
  <section class="about-section" id="about">
    <div class="about-content">
      <h2>Sujit Luintel</h2>
      <p>This is a fully automated AI blog that discovers trending topics in AI and automation, writes insightful articles, and publishes them — every single day, with zero human intervention.</p>
      <p>Powered by <strong>Gemini AI</strong> · <strong>Google Trends</strong> · <strong>GitHub Actions</strong> · <strong>Pexels</strong> · <strong>Unsplash</strong></p>
    </div>
  </section>
  <footer class="site-footer">
    <p>© {year} Sujit Luintel · AI Tools &amp; Automation Insights</p>
    <p style="margin-top:.25rem;">Auto-published with AI · Powered by Gemini &amp; GitHub Actions</p>
  </footer>
</body>
</html>"""


# ─────────────────────────────────────────
# 9. REGENERATE sitemap.xml
# ─────────────────────────────────────────
def build_sitemap(posts):
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    homepage_block = f"""
<url>
  <loc>{SITE_URL}/</loc>
  <lastmod>{now_iso}</lastmod>
  <priority>1.00</priority>
</url>"""
    post_blocks = ""
    for p in posts:
        post_blocks += f"""
<url>
  <loc>{SITE_URL}/{p['url']}</loc>
  <lastmod>{now_iso}</lastmod>
  <priority>0.80</priority>
</url>"""
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset
      xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9
            http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">
<!-- generated by sluintel.github.io auto-blog -->
{homepage_block}
{post_blocks}

</urlset>"""
    SITEMAP_PATH.write_text(xml.strip(), encoding="utf-8")
    print(f"✅ sitemap.xml updated ({len(posts)} posts + 1 homepage)")


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
    print(f"✅ llms.txt updated ({total} posts)")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    print("\n🤖 Auto Blog Generator starting…\n")
    POSTS_DIR.mkdir(exist_ok=True)
    OG_DIR.mkdir(parents=True, exist_ok=True)

    keyword             = get_trending_keyword()
    post                = generate_blog_post(keyword)
    img_url, img_credit = get_feature_image(keyword)
    og_image_url        = generate_og_image(post["title"], post["slug"])

    date_str        = datetime.now().strftime("%Y-%m-%d")
    posts, filename = update_posts_json(post, img_url, date_str)

    post_html = build_post_html(post, img_url, img_credit, og_image_url, date_str)
    post_path = POSTS_DIR / filename
    post_path.write_text(post_html, encoding="utf-8")
    print(f"✅ Post written → posts/{filename}")

    INDEX_HTML.write_text(build_index_html(posts), encoding="utf-8")
    print("✅ index.html regenerated")

    build_sitemap(posts)
    build_llms_txt(posts)

    print(f"\n🎉 Done! '{post['title']}' is live at posts/{filename}\n")


if __name__ == "__main__":
    main()
