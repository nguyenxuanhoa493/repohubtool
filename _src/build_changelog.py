#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render the changelog in both languages.

    python3 _src/build_changelog.py

Writes changelog/index.html and vi/changelog/index.html, sharing build.py's CSS
and top menu so the three pages of this site stay one site.

Noi dung nam trong changelogs.json o goc repo - nguon duy nhat cho changelog,
thong bao Telegram va manifest.note. Them mot ban phat hanh = them mot object vao
mang "releases"; file nay chi lo viec render.

Headline cua moi muc chinh la cau ma ban phat hanh do da hien tren man cap nhat,
nen trang changelog khong the ke ve mot phien ban dieu no khong lam. Danh sach bat
dau tu 1.32: do la luc man cap nhat co dong "co gi moi", va khong bia gi cho cac
ban truoc do.
"""

import json
import os
import re

from build import CSS, DOMAIN, navlinks_for

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (version, date, (en headline, vi headline), [(en detail, vi detail), ...])
# Headlines are verbatim from each release's own note. Details are only filled
# in where the change is worth more than a line; an empty list is honest.
CHANGELOG_FILE = os.path.join(ROOT, "changelogs.json")

def load_releases(path=None):
    """Doc changelogs.json - nguon duy nhat cho changelog cua moi phien ban.

    Them mot ban phat hanh = them mot object vao mang "releases" trong file JSON,
    khong phai sua code. Tra ve dung dang ma phan render dang dung:
    [(version, date, (headline_en, headline_vi), [(bullet_en, bullet_vi), ...])]
    """
    with open(path or CHANGELOG_FILE, encoding="utf-8") as f:
        doc = json.load(f)
    out = []
    for rel in doc.get("releases", []):
        head = rel.get("headline") or {}
        bullets = rel.get("bullets") or []
        out.append((
            str(rel.get("version", "")),
            str(rel.get("date", "")),
            (head.get("en", ""), head.get("vi", "")),
            [(b.get("en", ""), b.get("vi", "")) for b in bullets],
        ))
    return out

RELEASES = load_releases()

EXTRA_CSS = """
  main.guide{max-width:820px}
  .log{list-style:none;padding:0;margin:0;position:relative}
  .log::before{content:"";position:absolute;left:13px;top:14px;bottom:14px;
    width:2px;background:var(--line)}
  .log li{position:relative;padding:0 0 32px 46px}
  .log li:last-child{padding-bottom:0}
  .log .pin{position:absolute;left:4px;top:4px;width:20px;height:20px;border-radius:50%;
    background:var(--bg);border:2px solid var(--line)}
  .log li.newest .pin{border-color:var(--accent);background:var(--accent);
    box-shadow:0 0 14px rgba(0,246,246,.6)}
  .vtag{display:flex;align-items:baseline;gap:12px;margin-bottom:4px;flex-wrap:wrap}
  .vtag b{font-size:1.18rem;color:var(--accent);letter-spacing:-.2px}
  .vtag time{color:var(--muted);font-size:.86rem;font-variant-numeric:tabular-nums}
  .log h3{margin:2px 0 8px;font-size:1.05rem;line-height:1.45;font-weight:600}
  .log ul{margin:8px 0 0;padding-left:20px;color:var(--muted);font-size:.92rem}
  .log ul li{padding:0 0 6px 0;line-height:1.55}
  .log ul li:last-child{padding-bottom:0}
  .log ul li code{font-size:.85em}
  .badge.ok{background:rgba(0,246,246,.14);color:var(--accent);
    border:1px solid rgba(0,246,246,.45);font-size:.72rem;padding:2px 8px;
    border-radius:999px;font-weight:700;letter-spacing:.03em;text-transform:uppercase}
  .foot{margin-top:40px;padding-top:20px;border-top:1px solid var(--line);
    color:var(--muted);font-size:.88rem;line-height:1.6}
  .foot a{color:var(--accent);text-decoration:none}
  .foot a:hover{text-decoration:underline}
"""

T = {
 "en": {
  "lang": "en", "other": "vi", "other_name": "Tiếng Việt",
  "home": "/", "self": "/changelog/", "otherself": "/vi/changelog/",
  "title": "Changelog — RetroHub",
  "desc": "What changed in each version of RetroHub, lifted straight from the notes that shipped with the updates.",
  "keywords": "RetroHub, changelog, release notes, TrimUI Brick, updates, retro handheld",
  "og_desc": "Every update note since 1.32, word for word.",
  "h1": "Changelog",
  "lead": ("Every release note since 1.32 — the same sentence the update screen on your "
           "device showed when the build arrived."),
  "back": "Back to homepage",
  "latest": "Latest",
  "foot": ('Looking for source commits? The repository and full release history '
           'live on <a href="https://github.com/nguyenxuanhoa493/repohubtool/releases">GitHub</a>.'),
 },
 "vi": {
  "lang": "vi", "other": "en", "other_name": "English",
  "home": "/vi/", "self": "/vi/changelog/", "otherself": "/changelog/",
  "title": "Nhật ký bản phát hành — RetroHub",
  "desc": "Những thay đổi qua từng phiên bản RetroHub, trích nguyên văn từ ghi chú đi kèm mỗi bản cập nhật.",
  "keywords": "RetroHub, nhật ký thay đổi, release notes, TrimUI Brick, cập nhật, máy chơi game cầm tay",
  "og_desc": "Toàn bộ ghi chú phát hành từ bản 1.32 đến nay, nguyên văn từng câu.",
  "h1": "Nhật ký bản phát hành",
  "lead": ("Toàn bộ ghi chú cập nhật từ bản 1.32 — đúng câu mà màn hình cập nhật trên "
           "máy bạn đã hiện khi có bản mới."),
  "back": "Về trang chủ",
  "latest": "Mới nhất",
  "foot": ('Cần xem lịch sử mã nguồn? Toàn bộ commit và tệp phân phối '
           'của từng phiên bản nằm trên '
           '<a href="https://github.com/nguyenxuanhoa493/repohubtool/releases">GitHub</a>.'),
 },
}

PAGE = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="keywords" content="{keywords}">
<meta name="author" content="Nguyễn Xuân Hòa">
<meta name="robots" content="index, follow">
<meta name="theme-color" content="#0d1220">
<link rel="canonical" href="{canon}">
<link rel="alternate" hreflang="en" href="{DOMAIN}/changelog/">
<link rel="alternate" hreflang="vi" href="{DOMAIN}/vi/changelog/">
<link rel="alternate" hreflang="x-default" href="{DOMAIN}/changelog/">
<link rel="icon" href="/logo.png">
<link rel="apple-touch-icon" href="/logo.png">
<meta property="og:type" content="website">
<meta property="og:locale" content="{oglocale}">
<meta property="og:site_name" content="RetroHub">
<meta property="og:url" content="{canon}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{og_desc}">
<meta property="og:image" content="{DOMAIN}/og-{lang}.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{og_desc}">
<meta name="twitter:image" content="{DOMAIN}/og-{lang}.png">
<script type="application/ld+json">
{ldjson}
</script>
<style>{css}{extracss}</style>
</head>
<body>

<nav>
  <div class="navin">
    <a class="brand" href="{home}"><img src="/logo.png" alt=""><span>RetroHub</span></a>
    <div class="navlinks">{navlinks}</div>
    <a class="lang" href="{otherself}" hreflang="{other}" title="{other_name}">
      <img src="/files/assets/flag_{other}.png" alt=""><span>{other_name}</span></a>
  </div>
</nav>

<header style="padding:56px 0 34px">
  <div class="wrap">
    <h1 style="margin-top:0">{h1}</h1>
    <p class="sub" style="max-width:720px;margin:0 auto">{lead}</p>
  </div>
</header>

<main class="wrap guide" style="padding-bottom:64px">
  <section class="rise" style="padding-top:14px">
    <ul class="log">{entries}</ul>
    <p class="foot">{foot}</p>
    <p style="margin-top:26px"><a class="btn ghost" href="{home}">{back}</a></p>
  </section>
</main>

<script>
  (function(){
    var els = document.querySelectorAll('.rise');
    if (!('IntersectionObserver' in window) ||
        window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      els.forEach(function(el){ el.classList.add('seen'); });
      return;
    }
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(e){
        if (e.isIntersecting) { e.target.classList.add('seen'); io.unobserve(e.target); }
      });
    }, {rootMargin: '0px 0px -60px 0px'});
    els.forEach(function(el){ io.observe(el); });
  })();
</script>
</body>
</html>
"""


def render(lang):
    t = T[lang]
    canon = DOMAIN + t["self"]
    i = 0 if lang == "en" else 1

    rows = []
    for n, (ver, date, head, details) in enumerate(RELEASES):
        badge = ('<span class="badge ok">%s</span>' % t["latest"]) if n == 0 else ""
        bullets = ""
        if details:
            bullets = "<ul>%s</ul>" % "".join("<li>%s</li>" % d[i] for d in details)
        rows.append(
            '<li class="%s"><span class="pin"></span>'
            '<span class="vtag"><b>%s</b><time datetime="%s">%s</time>%s</span>'
            '<h3>%s</h3>%s</li>'
            % ("newest" if n == 0 else "", ver, date, date, badge, head[i], bullets))

    ld = {
        "@context": "https://schema.org", "@type": "WebPage",
        "name": t["title"], "description": t["desc"], "inLanguage": lang,
        "url": canon, "isPartOf": {"@type": "WebSite", "name": "RetroHub", "url": DOMAIN},
    }

    out = PAGE
    for k, v in {
        "lang": lang, "canon": canon, "DOMAIN": DOMAIN,
        "oglocale": "en_US" if lang == "en" else "vi_VN",
        "ldjson": json.dumps(ld, ensure_ascii=False, indent=2),
        "css": CSS, "extracss": EXTRA_CSS,
        "home": t["home"],
        "otherself": t["otherself"],
        "other": t["other"],
        "other_name": t["other_name"],
        "navlinks": navlinks_for(lang, "changelog"),
        "entries": "".join(rows),
    }.items():
        out = out.replace("{%s}" % k, str(v))
    for k, v in t.items():
        if isinstance(v, str):
            out = out.replace("{%s}" % k, v)

    left = re.findall(r"\{([a-zA-Z_]+)\}", out)
    if left:
        raise SystemExit("con cho trong chua thay: %s" % sorted(set(left)))
    return out


def main():
    for lang in ("en", "vi"):
        path = os.path.join(ROOT, "changelog/index.html" if lang == "en"
                            else "vi/changelog/index.html")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(render(lang))
        print("  %-26s %6d byte" % (os.path.relpath(path, ROOT), os.path.getsize(path)))


if __name__ == "__main__":
    main()
