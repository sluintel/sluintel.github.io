# 🤖 Sujit Luintel — AI Tools & Automation Blog

> A fully automated AI blog by **[Sujit Luintel](https://sluintel.com.np)** — Digital Strategist, Author, and Digital Marketing Expert from Kathmandu, Nepal.

**Automated Blog Post Website:** [https://sluintel.github.io](https://sluintel.github.io)  
**Personal website:** [https://sluintel.com.np](https://sluintel.com.np)

---

## How It Works

```
Google Trends → Gemini AI → Unsplash → GitHub Actions → GitHub Pages
(keyword)       (writes post)  (image)    (twice daily)   (live site)
```

Every day at **6:45 AM and 6:55 PM Nepal time**, GitHub Actions automatically:

1. Fetches the most trending AI keyword from Google Trends
2. Generates a full SEO-optimised blog post using Gemini 2.5 Flash
3. Downloads a royalty-free feature image from Unsplash
4. Saves the post as an HTML file inside `posts/`
5. Updates `posts.json`, `index.html`, `sitemap.xml`, and `llms.txt`
6. Commits and pushes everything to GitHub Pages

**Zero human interaction required.**

---

## Tech Stack

| Layer | Technology |
|---|---|
| Content Generation | Gemini 2.5 Flash (Google AI) |
| Trend Discovery | Google Trends via `pytrends` |
| Feature Images | Unsplash API |
| Hosting | GitHub Pages |
| Automation | GitHub Actions (cron schedule) |
| Analytics | Google Analytics (GA4) |
| Language | Python 3.11 |

---

## File Structure

```
sluintel.github.io/
├── index.html              ← Homepage (auto-regenerated on every run)
├── style.css               ← Dark tech theme with purple/cyan accents
├── 404.html                ← Custom 404 page
├── sitemap.xml             ← Auto-updated sitemap (Google Search Console)
├── robots.txt              ← Crawler rules pointing to sitemap
├── llms.txt                ← AI/LLM context file (auto-updated)
├── posts.json              ← Index of all posts (auto-updated)
├── used_keywords.json      ← Prevents duplicate keyword usage
├── requirements.txt        ← Python dependencies
├── .nojekyll               ← Disables Jekyll; enables raw static serving
├── scripts/
│   └── generate_post.py   ← Main automation script (all logic here)
├── posts/
│   └── YYYY-MM-DD-slug.html  ← Auto-generated blog posts
└── .github/
    └── workflows/
        ├── auto-blog.yml  ← Main daily publishing workflow
        └── keep-alive.yml ← Weekly workflow to keep schedule active
```

---

## Setup Guide

### Step 1 — Get Your API Keys

**Gemini API Key**
1. Go to [aistudio.google.com/api-keys](https://aistudio.google.com/api-keys)
2. Click **Create API Key** → copy it (starts with `AI...`)
3. Free tier: 1,500 requests/day — more than enough

**Unsplash API Key**
1. Go to [unsplash.com/developers](https://unsplash.com/developers)
2. Create a new application → copy your **Access Key**
3. Free tier: 50 requests/hour

---

### Step 2 — Fork or Clone This Repo

```bash
git clone https://github.com/sluintel/sluintel.github.io.git
cd sluintel.github.io
```

Or click **Fork** on GitHub to create your own copy.

---

### Step 3 — Add Secrets to GitHub

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret Name | Value |
|---|---|
| `GEMINI_API_KEY` | Your Gemini API key |
| `UNSPLASH_ACCESS_KEY` | Your Unsplash Access Key |

---

### Step 4 — Enable GitHub Pages

1. Repo → **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` → Folder: `/ (root)`
4. Click **Save**

Your site goes live at `https://YOUR-USERNAME.github.io` within 2 minutes.

---

### Step 5 — Customise for Your Brand

**Change the blog name/author**
Edit `SITE_URL`, `BLOG_TITLE`, and author references in `scripts/generate_post.py`

**Change the niche/topic**
Edit `FALLBACK_KEYWORDS` and `TREND_SEEDS` in `scripts/generate_post.py`

**Change posting frequency**
Edit `.github/workflows/auto-blog.yml`:
```yaml
- cron: '0 1 * * *'     # Once daily
- cron: '15 1 */2 * *'  # Every 2 days
- cron: '0 1 * * 1'     # Weekly (Mondays only)
```

**Change the theme colours**
Edit CSS variables at the top of `style.css`

---

### Step 6 — Trigger Your First Post

1. Go to **Actions** tab in your repo
2. Click **🤖 Auto Blog Publisher**
3. Click **Run workflow** → **Run workflow**
4. Wait ~60 seconds → visit your live site

---

## Key Features

- **Duplicate prevention** — `used_keywords.json` tracks all used keywords, ensuring every post covers a fresh topic
- **Crash-safe JSON** — both `posts.json` and `used_keywords.json` use safe-read guards that self-heal if a file becomes corrupted mid-run
- **Auto sitemap** — `sitemap.xml` is regenerated on every run with a fresh `lastmod` timestamp, keeping Google Search Console happy
- **llms.txt** — structured context file for AI crawlers (ChatGPT, Perplexity, Claude) linking this blog to Sujit Luintel's authority
- **Keep-alive workflow** — a weekly GitHub Actions job prevents GitHub from disabling the cron schedule due to inactivity
- **Fallback pool** — if Google Trends is rate-limited, the script picks from a curated keyword list and continues without failing

---

## Cost

| Service | Cost |
|---|---|
| GitHub Pages | **Free** |
| GitHub Actions | **Free** (2,000 min/month included) |
| Unsplash API | **Free** (50 req/hour) |
| Gemini 2.5 Flash | **Free** (1,500 req/day) |
| **Total** | **$0/month** |

---

## About the Author

**Sujit Luintel** is a Digital Strategist, Author, and Digital Marketing Expert based in Kathmandu, Nepal. He specialises in digital brand building, SEO systems, AI-driven marketing automation, and content-led growth strategies.

- 🌐 Personal website: [sluintel.com.np](https://sluintel.com.np)
- 📖 Books, consulting, and digital strategy writing available at the personal site
- 🤖 This blog demonstrates Sujit Luintel's expertise in building intelligent, fully automated content systems

---

## Troubleshooting

**Action fails with API error**
→ Check **Settings → Secrets → Actions** — ensure both secrets are set correctly

**Posts not appearing on homepage**
→ The Action may have written the HTML file but failed before updating `posts.json`. Manually add the post entry to `posts.json` matching the filename in `posts/`

**Google Trends rate limited**
→ Expected and handled automatically. The script falls back to the curated keyword pool and continues without any action needed

**Sitemap showing "Couldn't fetch" in Search Console**
→ Search Console caches failures for 3–7 days. Visit `https://your-site/sitemap.xml` directly in a browser to confirm it loads, then use the refresh button in Search Console

**Schedule not triggering automatically**
→ GitHub disables cron workflows after 60 days of no activity. The included `keep-alive.yml` workflow runs every Sunday to prevent this. If it has already stopped, go to Actions → run any workflow manually once to re-register the schedule

---

*Auto-published with AI · Powered by Gemini & GitHub Actions*
