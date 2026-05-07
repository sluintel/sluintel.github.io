# SluIntel — Automated AI Blog

> **AI Tools & Automation** insights, auto-published daily to GitHub Pages.

---

## How It Works

```
Google Trends  →  Claude AI  →  Unsplash  →  GitHub Actions  →  GitHub Pages
(trending keyword)  (writes post)  (feature image)  (daily cron)  (sluintel.github.io)
```

Every day at **6:45 AM Nepal time**, GitHub Actions:
1. Fetches the most trending AI keyword from Google Trends
2. Asks Claude AI to write a full SEO blog post
3. Downloads a royalty-free feature image from Unsplash
4. Commits the new HTML post to the repo
5. Regenerates `index.html` with the new post card

**Zero human interaction required.**

---

## Setup Guide

### Step 1 — Get Your API Keys

#### A. Anthropic (Claude) API Key
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up / log in
3. Click **"API Keys"** in the left sidebar
4. Click **"Create Key"** → copy the key (starts with `sk-ant-...`)
5. New accounts get **$5 free credits** (≈ 100+ blog posts)

#### B. Unsplash API Key
1. Go to [unsplash.com/developers](https://unsplash.com/developers)
2. Sign up / log in → click **"Your Applications"**
3. Click **"New Application"** → accept terms
4. Fill in: App name = `SluIntel Blog`, Description = `Auto blog images`
5. Scroll down → copy your **Access Key** (free — 50 requests/hour)

---

### Step 2 — Set Up GitHub Repository

1. Go to [github.com](https://github.com) and log in
2. Create a **new repository** named exactly: `sluintel.github.io`
   - Owner: your GitHub username (must be `sluintel`)
   - Visibility: **Public**
   - ✅ Check "Add a README file"
3. Click **Create repository**

---

### Step 3 — Upload the Project Files

**Option A — GitHub Web UI (easiest for beginners):**

1. Download the ZIP file you received
2. Unzip it on your computer
3. In your GitHub repo, click **"Add file"** → **"Upload files"**
4. Drag ALL the files/folders into the upload area:
   - `index.html`
   - `style.css`
   - `404.html`
   - `posts.json`
   - `used_keywords.json`
   - `requirements.txt`
   - `scripts/` (folder with `generate_post.py`)
   - `.github/` (folder with `workflows/auto-blog.yml`)
5. Commit message: `Initial setup`
6. Click **Commit changes**

> ⚠️ **Important:** The `.github` folder might be hidden on your computer (Mac/Linux). Press `Cmd+Shift+.` (Mac) or enable "Show hidden files" (Windows) to see it.

**Option B — Git command line:**
```bash
git clone https://github.com/sluintel/sluintel.github.io.git
cd sluintel.github.io
# Copy all project files here
git add -A
git commit -m "Initial setup"
git push
```

---

### Step 4 — Add Secret API Keys to GitHub

1. In your repo, click **Settings** (top menu)
2. In the left sidebar → **Secrets and variables** → **Actions**
3. Click **"New repository secret"** and add these two:

| Secret Name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Claude API key (`sk-ant-...`) |
| `UNSPLASH_ACCESS_KEY` | Your Unsplash Access Key |

---

### Step 5 — Enable GitHub Pages

1. In your repo → **Settings** → **Pages** (left sidebar)
2. Under **Source** → select **"Deploy from a branch"**
3. Branch: **`main`** → Folder: **`/ (root)`**
4. Click **Save**
5. Wait 1-2 minutes → your site is live at `https://sluintel.github.io`

---

### Step 6 — Trigger Your First Post

Don't wait for the daily cron — trigger it manually right now:

1. In your repo → **Actions** tab
2. Click **"🤖 Auto Blog Publisher"** in the left list
3. Click **"Run workflow"** → **"Run workflow"** (green button)
4. Watch it run! (takes about 30-60 seconds)
5. After it finishes, visit `https://sluintel.github.io` — your first post is live! 🎉

---

## File Structure

```
sluintel.github.io/
├── index.html              ← Homepage (auto-regenerated daily)
├── style.css               ← Dark theme styles
├── 404.html                ← Custom 404 page
├── posts.json              ← Index of all posts (auto-updated)
├── used_keywords.json      ← Prevents duplicate keywords
├── requirements.txt        ← Python packages
├── scripts/
│   └── generate_post.py   ← Main automation script
├── posts/
│   └── YYYY-MM-DD-slug.html  ← Generated blog posts
└── .github/
    └── workflows/
        └── auto-blog.yml  ← Daily automation schedule
```

---

## Cost Estimate (Monthly)

| Service | Cost |
|---|---|
| GitHub Pages | **Free** |
| GitHub Actions | **Free** (2,000 min/month included) |
| Unsplash API | **Free** (50 req/hour) |
| Claude API | ~$0.50–$2/month (for 30 posts) |

**Total: Under $2/month** (just the Claude API calls)

---

## Customisation

**Change posting frequency:** Edit `.github/workflows/auto-blog.yml`
```yaml
- cron: '15 1 * * *'    # Daily (current)
- cron: '15 1 */2 * *'  # Every 2 days
- cron: '15 1 * * 1'    # Weekly (Mondays)
```

**Change niche/topic:** Edit `FALLBACK_KEYWORDS` and `TREND_SEEDS` in `scripts/generate_post.py`

**Change blog name:** Edit `BLOG_TITLE` in `generate_post.py` and update `index.html`/`style.css` logo text

---

## Troubleshooting

**Action fails with API error:**
→ Double-check your secrets in Settings → Secrets → Actions

**Site not showing at sluintel.github.io:**
→ Settings → Pages → make sure branch is set to `main`

**pytrends rate limited:**
→ The script automatically falls back to the curated keyword pool. No action needed.

**Posts not appearing:**
→ Check the Actions tab for error logs
