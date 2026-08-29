#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render the changelog in both languages.

    python3 _src/build_changelog.py

Writes changelog/index.html and vi/changelog/index.html, sharing build.py's CSS
and top menu so the three pages of this site stay one site.

The headline of each entry is the note that version actually shipped with - the
same sentence the app showed on its update screen, lifted from the history of
manifest.json rather than rewritten here, so the page cannot claim a version did
something it did not. Notes begin at 1.32; that is when the update screen gained
a "what changed" line, and nothing is invented for the builds before it.
"""

import json
import os
import re

from build import CSS, DOMAIN, navlinks_for

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (version, date, (en headline, vi headline), [(en detail, vi detail), ...])
# Headlines are verbatim from each release's own note. Details are only filled
# in where the change is worth more than a line; an empty list is honest.
RELEASES = [
    ("1.44", "2026-08-30",
     ("Java games with a space in the filename now open",
      "Game Java có dấu cách trong tên tệp giờ mở được"),
     [("The emulator opens a jar through a \"jar:file:\" URI it never escapes, so one "
       "space and it could not read the manifest — the game died before drawing a frame. "
       "758 of the 3,357 Java sources in the library are named that way.",
       "Giả lập mở tệp jar bằng một URI \"jar:file:\" mà không mã hoá gì cả, nên chỉ một "
       "dấu cách là không đọc nổi manifest — game chết trước khi vẽ được khung hình nào. "
       "758 trên 3.357 nguồn game Java trong kho có tên như vậy."),
      ("Files already on the card are renamed when the app opens; saves, per-game "
       "settings and box art are renamed with them.",
       "Tệp đã nằm sẵn trên thẻ được đổi tên khi mở app; save game, cấu hình riêng từng "
       "game và ảnh bìa đổi theo cùng.")]),

    ("1.43", "2026-08-30",
     ("A device still on the old Java emulator is upgraded automatically",
      "Máy còn giả lập Java cũ được tự nâng cấp"),
     [("An in-app update carries the app only, not the 66 MB emulator, so a device could "
       "sit on the old one indefinitely with nothing saying so. Now the app notices and "
       "upgrades it at startup, keeping saves.",
       "Bản cập nhật trong app chỉ mang mã ứng dụng, không mang 66 MB giả lập, nên máy có "
       "thể ở lại bản cũ mãi mà không ai báo. Giờ app tự nhận ra và nâng cấp lúc khởi "
       "động, giữ nguyên save.")]),

    ("1.42", "2026-08-30",
     ("Reinstalling the Java emulator no longer wipes saves",
      "Cài lại giả lập Java không còn xoá save game"),
     [("J2ME saves and per-game settings live inside the emulator folder, and reinstalling "
       "replaced that folder wholesale. They are now moved aside and put back — including "
       "when the install fails halfway.",
       "Save J2ME và cấu hình từng game nằm bên trong thư mục giả lập, mà cài lại thì thay "
       "trọn thư mục đó. Giờ chúng được cất ra rồi đặt lại — kể cả khi bản cài hỏng giữa "
       "chừng.")]),

    ("1.41", "2026-08-30",
     ("New FreeJ2ME build for the Brick Pro",
      "Giả lập Java đổi sang bản FreeJ2ME mới cho Brick Pro"),
     [("Three display modes — PIXEL, SMOOTH, HQ — switchable in the app or with START + R3 "
       "in game.",
       "Ba kiểu hiển thị PIXEL, SMOOTH, HQ — đổi trong app hoặc bấm START + R3 ngay trong "
       "game."),
      ("Pad layouts H, K and X cycle on the device with START + SELECT, and quitting a game "
       "now asks first.",
       "Ba bố trí nút H, K, X đổi ngay trên máy bằng START + SELECT, và thoát game giờ có "
       "hỏi lại.")]),

    ("1.40", "2026-08-29",
     ("Vietnamese text no longer shows as boxes on font-poor themes",
      "Chữ tiếng Việt không còn thành ô vuông trên máy dùng theme thiếu font"),
     []),

    ("1.39", "2026-08-29",
     ("The game library updates in place, no reinstall",
      "Kho game tự cập nhật trong máy, không cần cài lại"),
     []),

    ("1.38", "2026-08-29",
     ("No more placeholder box art; games without a cover show a name-and-system tile",
      "Không còn ảnh 404 ở box art; game chưa có bìa hiện ô tên game và hệ máy"),
     []),

    ("1.37", "2026-08-29",
     ("Alphabet jump lands on the right game, with no column drift",
      "Nhảy chữ cái rơi đúng game, không còn lệch cột"),
     []),

    ("1.36", "2026-08-29",
     ("The game list no longer stops at 1,000 entries",
      "Danh sách game không còn cắt ngang ở 1.000"),
     []),

    ("1.35", "2026-08-29",
     ("Games launch with the emulator and mode the device has selected",
      "Mở game bằng đúng giả lập và đúng chế độ máy đang chọn"),
     []),

    ("1.34", "2026-08-29",
     ("Extracted games keep their proper name; the file is named on screen",
      "Game giải nén xong giữ đúng tên, màn hình báo rõ file nào"),
     []),

    ("1.33", "2026-08-29",
     ("Downloads in .rar/.7z now extract to a real ROM",
      "Tải game .rar/.7z giờ tự giải nén ra ROM thật"),
     []),

    ("1.32", "2026-08-29",
     ("Owned games open play/delete, not the download prompt",
      "Game đã tải mở bảng chơi/xoá/tải lại thay vì hỏi tải"),
     []),
]

EXTRA_CSS = """
  .guide p{color:var(--muted)}
  .log{list-style:none;padding:0;margin:0;position:relative}
  .log::before{content:"";position:absolute;left:11px;top:12px;bottom:12px;
    width:2px;background:var(--line)}
  .log > li{position:relative;padding:0 0 26px 42px}
  .log > li:last-child{padding-bottom:0}
  .log .pin{position:absolute;left:2px;top:5px;width:20px;height:20px;
    border-radius:50%;background:var(--bg);border:2px solid var(--line)}
  .log > li.newest .pin{border-color:var(--accent);background:var(--accent);
    box-shadow:0 0 12px rgba(0,246,246,.5)}
  .vtag{display:inline-flex;align-items:baseline;gap:10px;flex-wrap:wrap}
  .vtag b{font-size:1.06rem;font-variant-numeric:tabular-nums}
  .vtag time{color:var(--muted);font-size:.84rem}
  .vtag .badge{margin-left:0}
  .log h3{margin:4px 0 0;font-size:1rem;font-weight:600;color:var(--text)}
  .log ul{margin:10px 0 0;padding-left:20px;color:var(--muted);font-size:.93rem}
  .log ul li{margin:6px 0}
  .foot{color:var(--muted);font-size:.93rem;border-top:1px solid var(--line);
    margin-top:38px;padding-top:20px}
  .foot a{color:var(--accent);text-decoration:none}
  .foot a:hover{text-decoration:underline}
"""

T = {
 "en": {
  "lang": "en", "other": "vi", "other_name": "Tiếng Việt",
  "home": "/", "self": "/changelog/", "otherself": "/vi/changelog/",
  "title": "RetroHub changelog",
  "desc": ("Every RetroHub release and what it changed, newest first — the Java J2ME "
           "emulator, the game library, downloads and the update flow."),
  "keywords": "RetroHub, changelog, release notes, TrimUI Brick, version history",
  "og_desc": "Every RetroHub release and what changed in it, newest first.",
  "h1": "Changelog",
  "lead": ("Every release and what it changed, newest first. Each headline is the note "
           "that version actually shipped with — the same sentence the app shows on its "
           "update screen."),
  "latest": "Latest",
  "back": "Back to the home page",
  "foot": ('Builds before 1.32 predate the update screen\'s "what changed" line, so they '
           'are not listed here rather than described after the fact. Full notes and the '
           'download for each release are on '
           '<a href="https://github.com/nguyenxuanhoa493/repohubtool/releases">GitHub</a>.'),
 },
 "vi": {
  "lang": "vi", "other": "en", "other_name": "English",
  "home": "/vi/", "self": "/vi/changelog/", "otherself": "/changelog/",
  "title": "Nhật ký bản RetroHub",
  "desc": ("Từng bản RetroHub và những gì nó sửa, mới nhất trước — giả lập Java J2ME, "
           "kho game, tải game và luồng cập nhật."),
  "keywords": "RetroHub, nhật ký bản, changelog, TrimUI Brick, lịch sử phiên bản",
  "og_desc": "Từng bản RetroHub và những gì nó sửa, mới nhất trước.",
  "h1": "Nhật ký bản",
  "lead": ("Từng bản và những gì nó sửa, mới nhất trước. Mỗi dòng tiêu đề là ghi chú mà "
           "chính bản đó phát hành kèm — đúng câu app hiện trên màn cập nhật."),
  "latest": "Mới nhất",
  "back": "Về trang chủ",
  "foot": ('Các bản trước 1.32 ra đời khi màn cập nhật chưa có dòng "bản này sửa gì", nên '
           'không liệt kê ở đây thay vì mô tả lại theo trí nhớ. Ghi chú đầy đủ và bản tải '
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
