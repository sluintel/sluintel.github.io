#!/usr/bin/env python3
"""
migrate_posts.py — One-time script to update all existing post HTML files
                   to the new Sluintel nav/footer design.

RUN FROM YOUR REPO ROOT:
    python3 scripts/migrate_posts.py

WHAT IT DOES:
  - Reads every HTML file in /posts/ (skips /posts/og/)
  - Replaces old <header>, <footer>, fonts, and style.css link
  - Injects new nav (with hamburger), footer, CSS variables, theme toggle
  - Backs up each file to /posts/_backup/ before modifying
  - Prints a summary when done

SAFE TO RE-RUN: backs up before overwriting.
"""

import re
import sys
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
POSTS_DIR = REPO_ROOT / "posts"
BACKUP_DIR = POSTS_DIR / "_backup"

# ─── NEW FRAGMENTS ────────────────────────────────────────────────────────────

NEW_FONTS = """  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>"""

THEME_INIT_SCRIPT = """  <script>(function(){var t=localStorage.getItem('sl-theme');if(!t)t=window.matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light';document.documentElement.setAttribute('data-theme',t);})();</script>"""

NEW_CSS = """  <style>
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
/* ═══ ARTICLE LAYOUT ═══ */
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
/* Share */
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
/* Footer */
.sl-footer {
  border-top: 1px solid var(--border); padding: 32px 24px; background: var(--bg-2);
}
.sl-footer__inner {
  max-width: 1200px; margin: 0 auto;
  display: flex; justify-content: space-between; align-items: flex-start;
  flex-wrap: wrap; gap: 20px;
}
.sl-footer__brand {
  font-family: var(--font-display); font-size: 1.4rem; font-weight: 900;
}
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
/* Legacy compat: hide old elements if present */
.site-header, .site-footer, .nav-container, .nav-links,
.post-footer > .back-link:not(.sl-back-link),
.share-section, .image-credit { display: none !important; }
  </style>"""

NEW_NAV = """  <nav class="sl-nav" role="navigation" aria-label="Main navigation">
    <div class="sl-nav__inner">
      <a href="/" class="sl-nav__brand">Sujit <span> Luintel</span></a>
      <div class="sl-nav__links" id="navLinks">
        <a href="/#section-trending"      class="sl-nav__link">🔥 Trending</a>
        <a href="/#section-ai-automation" class="sl-nav__link">🤖 AI</a>
        <a href="/#section-sports"        class="sl-nav__link">⚽ Sports</a>
        <a href="/#section-finance"       class="sl-nav__link">💰 Finance</a>
        <a href="/#section-entertainment" class="sl-nav__link">🎬 Entertainment</a>
        <a href="/#section-technology"    class="sl-nav__link">💻 Tech</a>
        <a href="/#section-deep-dives"    class="sl-nav__link">🔍 Deep Dives</a>
        <a href="/#section-all"           class="sl-nav__link">📰 All Posts</a>
        <a href="/#about"                 class="sl-nav__link">About</a>
      </div>
      <div class="sl-nav__right">
        <button class="sl-ham" id="hamBtn" aria-label="Toggle menu" aria-expanded="false">
          <span class="bar"></span><span class="bar"></span><span class="bar"></span>
        </button>
        <button class="sl-theme-toggle" id="themeToggle" aria-label="Toggle theme">◐</button>
      </div>
    </div>
  </nav>"""

NEW_FOOTER_TEMPLATE = """  <footer class="sl-footer">
    <div class="sl-footer__inner">
      <div>
        <div class="sl-footer__brand">Slui<span>ntel</span></div>
        <div class="sl-footer__tagline">AI-powered daily blog by Sujit Luintel · Kathmandu, Nepal</div>
        <nav class="sl-footer__links" aria-label="Footer links">
          <a href="/#section-ai-automation">🤖 AI</a>
          <a href="/#section-sports">⚽ Sports</a>
          <a href="/#section-finance">💰 Finance</a>
          <a href="/#section-entertainment">🎬 Entertainment</a>
          <a href="/#section-technology">💻 Tech</a>
          <a href="/#section-trending">🔥 Trending</a>
        </nav>
      </div>
      <p class="sl-footer__copy">© {year} Sluintel · Content generated with AI · Auto-published via GitHub Actions</p>
    </div>
  </footer>"""

NEW_SCRIPTS = """  <script>
    (function(){var t=localStorage.getItem('sl-theme');if(!t)t=window.matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light';document.documentElement.setAttribute('data-theme',t);})();
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
  </script>"""


# ─── MIGRATION LOGIC ──────────────────────────────────────────────────────────

def extract_year_from_html(html: str) -> str:
    """Extract publish year from date in HTML or filename."""
    m = re.search(r'📅\s*(\w+\s+\d+,\s+(\d{4}))', html)
    if m:
        return m.group(2)
    m = re.search(r'(\d{4})-\d{2}-\d{2}', html)
    if m:
        return m.group(1)
    from datetime import datetime
    return str(datetime.now().year)


def migrate_post(filepath: Path) -> str:
    """Migrate a single post HTML file. Returns status string."""
    html = filepath.read_text(encoding="utf-8", errors="replace")

    # Skip already-migrated files (they have sl-nav class)
    if 'class="sl-nav"' in html:
        return "SKIP (already migrated)"

    # Backup
    BACKUP_DIR.mkdir(exist_ok=True)
    backup = BACKUP_DIR / filepath.name
    if not backup.exists():
        shutil.copy2(filepath, backup)

    year = extract_year_from_html(html)
    new_footer = NEW_FOOTER_TEMPLATE.format(year=year)

    # ── 1. Fix <html> tag: add data-theme ──────────────────────────────────
    html = re.sub(r'<html([^>]*)>', '<html\\1 data-theme="dark">', html, count=1)
    if 'data-theme' not in html[:200]:
        html = html.replace('<html', '<html data-theme="dark"', 1)

    # ── 2. Remove old font link (Inter) ────────────────────────────────────
    html = re.sub(
        r'<link[^>]*fonts\.googleapis\.com[^>]*Inter[^>]*/>\s*', '', html
    )
    html = re.sub(
        r'<link[^>]*fonts\.googleapis\.com[^>]*Fira[^>]*/>\s*', '', html
    )
    html = re.sub(
        r'<link[^>]*fonts\.gstatic\.com[^>]*/>\s*', '', html
    )
    html = re.sub(
        r'<link[^>]*fonts\.googleapis\.com[^>]*/>\s*', '', html
    )

    # ── 3. Remove old style.css link ───────────────────────────────────────
    html = re.sub(r'<link[^>]*style\.css[^>]*/>\s*', '', html)

    # ── 4. Remove old <style> blocks (share_css) ───────────────────────────
    html = re.sub(r'<style>\s*\.share-section[\s\S]*?</style>', '', html)

    # ── 5. Inject new CSS + fonts before </head> ───────────────────────────
    inject_head = f"\n{NEW_FONTS}\n{NEW_CSS}\n"
    html = html.replace('</head>', inject_head + '</head>', 1)

    # ── 6. Replace old <header> block with new nav ─────────────────────────
    # Pattern: <header class="site-header">...</header>
    html = re.sub(
        r'<header[^>]*class=["\']site-header["\'][^>]*>[\s\S]*?</header>',
        NEW_NAV,
        html,
        count=1
    )

    # ── 7. Replace <main class="post-main"> wrapper ────────────────────────
    # Wrap article content in sl-post-wrap
    # Find <main class="post-main"> and its inner <article class="post-article">
    if 'class="post-main"' in html:
        # Replace <main class="post-main"> → <div class="sl-post-wrap"> (approx)
        html = html.replace('<main class="post-main">', '<div class="sl-post-wrap-outer">', 1)
        html = html.replace('</main>', '</div>', 1)
        html = html.replace('<article class="post-article">', '<div class="sl-post-wrap">', 1)
        html = html.replace('</article>', '</div>', 1)

        # Update inner class names to new system
        html = html.replace('class="post-meta-top"', 'class="sl-post-tags"')
        html = html.replace('class="post-title"',    'class="sl-post-title"')
        html = html.replace('class="post-meta"',     'class="sl-post-meta"')
        html = html.replace('class="post-content"',  'class="sl-post-body"')
        html = html.replace('<span class="tag">',     '<span class="sl-post-tag">')
        html = html.replace('class="post-feature-image">', 'style="margin-bottom:8px">')

        # Feature image
        html = re.sub(
            r'<img\s+src="([^"]+)"\s+alt="([^"]+)"\s+loading="lazy"/>',
            r'<img class="sl-post-img" src="\1" alt="\2" loading="eager"/>',
            html, count=1
        )
        html = html.replace('class="image-credit"', 'class="sl-post-credit"')

        # Post footer
        html = html.replace('class="post-footer"', 'class="sl-post-footer"')
        html = html.replace('class="post-tags"',   'class="sl-post-tags"')
        html = html.replace('class="back-link"',   'class="sl-back-link"')

        # Share section → new classes
        html = html.replace('class="share-section"', 'class="sl-share"')
        html = html.replace('class="share-label"',   'class="sl-share-label"')
        html = html.replace('class="share-buttons"', 'class="sl-share-btns"')
        html = re.sub(r'class="share-btn share-(\w+)"', r'class="sl-share-btn sl-share-\1"', html)

        # Remove outer wrapper div
        html = html.replace('<div class="sl-post-wrap-outer">', '', 1)
        html = html.replace('</div><!-- closes sl-post-wrap-outer -->', '', 1)
        # The last </div> that was </main>
        html = re.sub(r'</div>\s*$', '', html.rstrip()) + '\n'

    # ── 8. Replace old <footer> ─────────────────────────────────────────────
    html = re.sub(
        r'<footer[^>]*class=["\']site-footer["\'][^>]*>[\s\S]*?</footer>',
        new_footer,
        html,
        count=1
    )

    # ── 9. Remove old inline share <script> ────────────────────────────────
    html = re.sub(r'<script>\s*function copyLink[\s\S]*?</script>', '', html)

    # ── 10. Inject new nav/theme/hamburger scripts before </body> ──────────
    html = html.replace('</body>', NEW_SCRIPTS + '\n</body>', 1)

    filepath.write_text(html, encoding="utf-8")
    return "OK"


def main():
    post_files = sorted([
        f for f in POSTS_DIR.glob("*.html")
        if f.is_file() and not f.name.startswith("_")
    ])

    if not post_files:
        print("No HTML files found in posts/")
        sys.exit(0)

    print(f"\n🔄 Migrating {len(post_files)} post files...\n")
    ok = skip = err = 0

    for fp in post_files:
        try:
            status = migrate_post(fp)
            icon = "✅" if status.startswith("OK") else ("⏭️ " if status.startswith("SKIP") else "❌")
            print(f"  {icon}  {fp.name:60s}  {status}")
            if status.startswith("OK"):
                ok += 1
            elif status.startswith("SKIP"):
                skip += 1
            else:
                err += 1
        except Exception as e:
            print(f"  ❌  {fp.name}: ERROR — {e}")
            err += 1

    print(f"\n{'─'*65}")
    print(f"  ✅ Migrated: {ok}   ⏭️  Skipped: {skip}   ❌ Errors: {err}")
    print(f"  📁 Backups in: posts/_backup/")
    if err == 0:
        print(f"\n  🎉 All done! Commit with:")
        print(f"     git add posts/ && git commit -m '🎨 Migrate all posts to new nav/footer design' && git push")
    else:
        print(f"\n  ⚠️  {err} files had errors. Check above. Backups are safe.")
    print()


if __name__ == "__main__":
    main()
