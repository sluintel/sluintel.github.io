#!/usr/bin/env python3
"""
SluIntel Auto Blog Generator
Niche: AI Tools & Automation
Runs daily via GitHub Actions
"""

import os
import json
import re
import random
import requests
from datetime import datetime
from pathlib import Path

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False

import anthropic

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
REPO_ROOT       = Path(__file__).parent.parent
POSTS_DIR       = REPO_ROOT / "posts"
POSTS_JSON      = REPO_ROOT / "posts.json"
USED_KW_FILE    = REPO_ROOT / "used_keywords.json"
INDEX_HTML      = REPO_ROOT / "index.html"

ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
UNSPLASH_KEY       = os.environ.get("UNSPLASH_ACCESS_KEY", "")

FALLBACK_KEYWORDS = [
    "best AI tools 2025",
    "AI automation for small business",
    "ChatGPT vs Claude vs Gemini",
    "no-code automation tools review",
    "AI writing tools comparison",
    "workflow automation with AI",
    "free AI image generation tools",
    "AI productivity tools for remote work",
    "how to automate your business with AI",
    "top AI SEO tools 2025",
    "AI tools for content creators",
    "make money with AI automation",
    "AI agents explained simply",
    "Zapier vs Make vs n8n comparison",
    "best AI code assistants 2025",
    "AI tools for email marketing",
    "how to use Claude AI effectively",
    "AI research tools for students",
    "AI video generation tools",
    "machine learning without coding",
]

TREND_SEEDS = [
    "AI tools", "automation software", "ChatGPT", "Claude AI",
    "Gemini AI", "AI agents", "no-code tools", "Copilot AI"
]


# ─────────────────────────────────────────
# 1. KEYWORD RESEARCH
# ─────────────────────────────────────────
def load_used_keywords():
    if USED_KW_FILE.exists():
        return json.loads(USED_KW_FILE.read_text())
    return []

def save_used_keyword(kw):
    used = load_used_keywords()
    used.append(kw)
    USED_KW_FILE.write_text(json.dumps(used[-40:], indent=2))

def get_trending_keyword():
    """Fetch trending AI keyword from Google Trends; fall back to curated list."""
    if PYTRENDS_AVAILABLE:
        try:
            pytrends = TrendReq(hl='en-US', tz=0, timeout=(10, 30),
                                retries=2, backoff_factor=0.5)
            batch = random.sample(TREND_SEEDS, min(5, len(TREND_SEEDS)))
            pytrends.build_payload(batch, timeframe='now 7-d', geo='')
            df = pytrends.interest_over_time()
            if not df.empty:
                top_kw = df.drop(columns=['isPartial'], errors='ignore').mean().idxmax()
                # Try to get a more specific related query
                pytrends.build_payload([top_kw], timeframe='now 7-d')
                related = pytrends.related_queries()
                rising = related.get(top_kw, {}).get('rising')
                if rising is not None and not rising.empty:
                    specific = rising.iloc[0]['query']
                    print(f"✅ Google Trends keyword: {specific}")
                    save_used_keyword(specific)
                    return specific
                print(f"✅ Google Trends keyword: {top_kw}")
                save_used_keyword(top_kw)
                return top_kw
        except Exception as e:
            print(f"⚠️  Google Trends error: {e} — using fallback pool")

    # Fallback: pick unused keyword from pool
    used = load_used_keywords()
    available = [k for k in FALLBACK_KEYWORDS if k not in used]
    if not available:
        available = FALLBACK_KEYWORDS
    kw = random.choice(available)
    save_used_keyword(kw)
    print(f"✅ Fallback keyword: {kw}")
    return kw


# ─────────────────────────────────────────
# 2. GENERATE BLOG POST WITH CLAUDE
# ─────────────────────────────────────────
def generate_blog_post(keyword):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""You are an expert tech blogger specialising in AI tools and automation.
Write a comprehensive, SEO-optimised blog post about: "{keyword}"

Return ONLY a valid JSON object — no markdown fences, no preamble, no trailing text.

JSON structure:
{{
  "title": "Engaging, click-worthy title under 65 characters",
  "meta_description": "Compelling meta description under 155 characters",
  "slug": "url-friendly-slug-with-hyphens-only",
  "tags": ["tag1", "tag2", "tag3"],
  "reading_time": "X min read",
  "content_html": "<p>Full blog post in HTML...</p> (800-1100 words, use h2 h3 p ul li strong em — no outer title or feature image)"
}}

Writing style: clear, practical, slightly opinionated. Include a compelling intro, 4-6 h2 sections with real value, bullet lists where helpful, and a strong conclusion with a CTA."""

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = msg.content[0].text.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    data = json.loads(raw)
    # Sanitise slug
    data['slug'] = re.sub(r'[^a-z0-9\-]', '', data['slug'].lower().replace(' ', '-'))
    print(f"✅ Post generated: {data['title']}")
    return data


# ─────────────────────────────────────────
# 3. FETCH FEATURE IMAGE (UNSPLASH)
# ─────────────────────────────────────────
def get_feature_image(keyword):
    FALLBACK_IMAGES = [
        "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=1200&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=1200&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1655720031554-a929595ffad7?w=1200&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1676299081847-824916de030a?w=1200&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=1200&auto=format&fit=crop",
    ]

    if UNSPLASH_KEY:
        try:
            q = " ".join(keyword.split()[:3]) + " technology AI"
            r = requests.get(
                "https://api.unsplash.com/photos/random",
                params={"query": q, "orientation": "landscape", "content_filter": "high"},
                headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"},
                timeout=10
            )
            if r.status_code == 200:
                d = r.json()
                img_url  = d['urls']['regular']
                name     = d['user']['name']
                link     = d['links']['html']
                credit   = f'Photo by <a href="{link}?utm_source=sluintel&utm_medium=referral" target="_blank" rel="noopener">{name}</a> on <a href="https://unsplash.com?utm_source=sluintel&utm_medium=referral" target="_blank" rel="noopener">Unsplash</a>'
                print(f"✅ Image by {name} from Unsplash")
                return img_url, credit
        except Exception as e:
            print(f"⚠️  Unsplash error: {e}")

    img = random.choice(FALLBACK_IMAGES)
    credit = 'Photo from <a href="https://unsplash.com" target="_blank" rel="noopener">Unsplash</a>'
    print("✅ Using fallback image")
    return img, credit


# ─────────────────────────────────────────
# 4. BUILD POST HTML FILE
# ─────────────────────────────────────────
def build_post_html(post, img_url, img_credit, date_str):
    tags_html   = "".join(f'<span class="tag">{t}</span>' for t in post['tags'])
    date_nice   = datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y')
    year        = datetime.now().year

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{post['title']} | SluIntel</title>
  <meta name="description" content="{post['meta_description']}"/>
  <meta property="og:title" content="{post['title']}"/>
  <meta property="og:description" content="{post['meta_description']}"/>
  <meta property="og:image" content="{img_url}"/>
  <meta property="og:type" content="article"/>
  <link rel="stylesheet" href="../style.css"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet"/>
</head>
<body>
  <header class="site-header">
    <nav class="nav-container">
      <a href="../index.html" class="logo">Slu<span>Intel</span></a>
      <div class="nav-links">
        <a href="../index.html">Home</a>
        <a href="../index.html#about">About</a>
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
          <span>⏱ {post.get('reading_time','5 min read')}</span>
        </div>
      </div>

      <div class="post-feature-image">
        <img src="{img_url}" alt="{post['title']}" loading="lazy"/>
        <p class="image-credit">{img_credit}</p>
      </div>

      <div class="post-content">
        {post['content_html']}
      </div>

      <div class="post-footer">
        <div class="post-tags"><strong>Tags:</strong> {tags_html}</div>
        <a href="../index.html" class="back-link">← Back to Home</a>
      </div>

    </article>
  </main>

  <footer class="site-footer">
    <p>© {year} SluIntel · AI Tools &amp; Automation Insights</p>
    <p style="margin-top:.25rem;">Auto-published with AI · Powered by Claude &amp; GitHub Actions</p>
  </footer>
</body>
</html>"""


# ─────────────────────────────────────────
# 5. UPDATE posts.json
# ─────────────────────────────────────────
def update_posts_json(post, img_url, date_str):
    posts = json.loads(POSTS_JSON.read_text()) if POSTS_JSON.exists() else []
    filename = f"{date_str}-{post['slug']}.html"
    entry = {
        "title":            post['title'],
        "slug":             post['slug'],
        "date":             date_str,
        "meta_description": post['meta_description'],
        "tags":             post['tags'],
        "image_url":        img_url,
        "reading_time":     post.get('reading_time', '5 min read'),
        "url":              f"posts/{filename}"
    }
    posts.insert(0, entry)
    POSTS_JSON.write_text(json.dumps(posts, indent=2))
    print(f"✅ posts.json updated  ({len(posts)} posts total)")
    return posts, filename


# ─────────────────────────────────────────
# 6. REGENERATE index.html
# ─────────────────────────────────────────
def build_index_html(posts):
    cards = ""
    for i, p in enumerate(posts):
        featured = " featured-card" if i == 0 else ""
        tags_html = "".join(f'<span class="tag">{t}</span>' for t in p['tags'][:2])
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
            <span>{p.get('reading_time','5 min read')}</span>
          </div>
        </div>
      </article>"""

    grid_inner = cards if cards else '<p class="no-posts">🚀 First post is being generated…</p>'
    year = datetime.now().year
    total = len(posts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>SluIntel — AI Tools &amp; Automation Insights</title>
  <meta name="description" content="Daily insights on AI tools, automation software, and the future of intelligent workflows. Stay ahead with SluIntel."/>
  <meta property="og:title" content="SluIntel — AI Tools &amp; Automation"/>
  <meta property="og:description" content="Daily AI tools and automation insights, auto-published every day."/>
  <link rel="stylesheet" href="style.css"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet"/>
</head>
<body>

  <header class="site-header">
    <nav class="nav-container">
      <a href="index.html" class="logo">Slu<span>Intel</span></a>
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
      <h2>About SluIntel</h2>
      <p>SluIntel is a fully automated AI blog that discovers trending topics in AI and automation, writes insightful articles, and publishes them — every single day, with zero human intervention.</p>
      <p>Powered by <strong>Claude AI</strong> · <strong>Google Trends</strong> · <strong>GitHub Actions</strong> · <strong>Unsplash</strong></p>
    </div>
  </section>

  <footer class="site-footer">
    <p>© {year} SluIntel · AI Tools &amp; Automation Insights</p>
    <p style="margin-top:.25rem;">Auto-published with AI · Powered by Claude &amp; GitHub Actions</p>
  </footer>

</body>
</html>"""


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    print("\n🚀 SluIntel Auto Blog Generator starting…\n")
    POSTS_DIR.mkdir(exist_ok=True)

    # 1. Keyword
    keyword = get_trending_keyword()

    # 2. Blog post
    post = generate_blog_post(keyword)

    # 3. Image
    img_url, img_credit = get_feature_image(keyword)

    # 4. Write post file
    date_str  = datetime.now().strftime('%Y-%m-%d')
    post_html = build_post_html(post, img_url, img_credit, date_str)
    posts, filename = update_posts_json(post, img_url, date_str)

    post_path = POSTS_DIR / filename
    post_path.write_text(post_html, encoding='utf-8')
    print(f"✅ Post written → posts/{filename}")

    # 5. Regenerate index
    index = build_index_html(posts)
    INDEX_HTML.write_text(index, encoding='utf-8')
    print("✅ index.html regenerated")

    print(f"\n🎉 Done! '{post['title']}' is live at posts/{filename}\n")


if __name__ == "__main__":
    main()
