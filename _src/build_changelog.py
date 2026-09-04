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
    ("1.56", "2026-09-04",
     ("New YouTube app: watch videos, search with on-screen keyboard, playback via RetroArch FFMPEG",
      "Thêm ứng dụng YouTube: xem video, tìm kiếm tiếng Việt, phát qua RetroArch FFMPEG"),
     [("Dedicated YouTube app on TrimUI handhelds with trending feed and fast switching between recent keywords using L1 / R1.",
       "Tích hợp ứng dụng YouTube xem video trực tiếp trên máy TrimUI, hỗ trợ duyệt video thịnh hành và chuyển nhanh từ khóa bằng nút L1 / R1."),
      ("On-screen keyboard with full Vietnamese accent input (TVTelex) and recent search history.",
       "Bàn phím ảo hỗ trợ gõ tiếng Việt có dấu (kiểu gõ TVTelex) cùng danh sách lưu lịch sử các từ khóa tìm kiếm gần đây."),
      ("Stream playback powered by RetroArch FFMPEG core with fast-forward, rewind, and volume controls.",
       "Phát video mượt mà qua core FFMPEG của RetroArch, điều khiển tua tiến, lùi và tăng giảm âm lượng dễ dàng."),
      ("Clear warning toast if RetroArch or FFMPEG core is not installed on the device.",
       "Thông báo trực quan khi máy chưa có sẵn RetroArch hoặc core FFMPEG thay vì thoát đột ngột.")]),

    ("1.55", "2026-09-03",
     ("LED lights now come back on their own after a reboot, on stock firmware too",
      "Đèn LED tự bật lại sau khi khởi động máy, dùng được trên cả firmware gốc"),
     [("Stock TrimUI firmware runs scripts from <code>/mnt/SDCARD/System/starts</code> without touching NAND flash.",
       "Firmware TrimUI gốc tự chạy các script từ <code>/mnt/SDCARD/System/starts</code> mà không cần can thiệp bộ nhớ NAND."),
      ("NextUI continues using <code>.hooks/boot.d</code>; 'Run at startup' now works on both systems.",
       "Hệ điều hành NextUI tiếp tục dùng <code>.hooks/boot.d</code>; tính năng 'Tự chạy khi khởi động' giờ hoạt động chuẩn trên cả hai hệ máy.")]),

    ("1.54", "2026-09-01",
     ("New LED Lights utility: 12 colour themes, 10 effects, live preview as you scroll",
      "Thêm tiện ích Đèn LED: 12 bộ màu, 10 hiệu ứng, xem thử ngay khi di con trỏ"),
     [("Custom software engine renders frame-by-frame into <code>/sys/class/led_anim</code>, enabling out-of-phase effects (wave, sweep) impossible with stock effects.",
       "Engine phần mềm tự vẽ từng khung hình vào <code>/sys/class/led_anim</code>, tạo được các hiệu ứng lệch pha (sóng chạy, quét) mà hiệu ứng gốc không làm được."),
      ("Background daemon preserves lighting effects even after exiting RetroHub.",
       "Daemon chạy nền giữ hiệu ứng đèn LED hoạt động ngay cả khi đã thoát RetroHub.")]),

    ("1.53", "2026-09-01",
     ("Fixes the overflowing badge in the emulator switcher",
      "Sửa nhãn tràn ra ngoài nút ở menu đổi giả lập"),
     []),

    ("1.52", "2026-09-01",
     ("NAOMI/Atomiswave games now route to the DC system; new emulator switcher in Utilities",
      "Game NAOMI/Atomiswave (Metal Slug 6, Marvel vs Capcom 2) về đúng hệ DC; thêm mục đổi giả lập trong Tiện ích"),
     []),

    ("1.51", "2026-08-31",
     ("Fixes CPS2 arcade games in the MAME system failing to launch",
      "Sửa game CPS2 hệ MAME (Marvel vs Capcom, Street Fighter Alpha...) không mở được"),
     []),

    ("1.50", "2026-08-31",
     ("Official NextUI support, dual artwork saving, and cleaner utilities menu",
      "Hỗ trợ chính thức hệ điều hành NextUI, lưu ảnh bìa kép và tinh gọn menu tiện ích"),
     [("Packaged as a native Tool Pak (<code>Tools/tg5040/RetroHub.pak</code> & <code>Tools/tg5050/</code>) with full in-app Wi-Fi auto-updates.",
       "Đóng gói dưới dạng Tool Pak (<code>Tools/tg5040/RetroHub.pak</code> & <code>Tools/tg5050/</code>) với đầy đủ tính năng tự cập nhật qua Wi-Fi."),
      ("ROM directories with NextUI tags like <code>Game Boy Advance (GBA)</code> are resolved automatically, and artwork is saved into <code>.media/</code> beside stock <code>Imgs/</code>.",
       "Tự động nhận diện thư mục ROM theo tag của NextUI như <code>Game Boy Advance (GBA)</code>, lưu ảnh bìa vào <code>.media/</code> song song với <code>Imgs/</code> của Stock OS."),
      ("Java J2ME installation now sets up <code>JAVA.pak</code> for NextUI as well as <code>Emus/JAVA</code> for Stock OS.",
       "Cài đặt giả lập Java J2ME tự động tạo <code>JAVA.pak</code> cho NextUI song song với <code>Emus/JAVA</code> cho Stock OS."),
      ("Fixed encrypted zip entry edge-case in Java jars refusing to launch.",
       "Sửa lỗi game Java chứa mục rỗng bị đánh dấu mã khoá làm không mở được."),
      ("Removed the redundant 'Reload ROMs' button from Utilities since NextUI scans games automatically.",
       "Loại bỏ nút 'Làm mới ROMs' trong Tiện ích vì NextUI tự động quét game khi về màn hình chính.")]),

    ("1.49", "2026-08-30",
     ("Java games at 320x240 no longer land in the 240320 folder",
      "Game Java 320x240 không còn rơi vào thư mục 240320"),
     []),

    ("1.48", "2026-08-30",
     ("Two pinned Java shelves and 130 more Gameloft titles",
      "Hai kệ game Java ghim đầu và thêm 130 game Gameloft"),
     []),

    ("1.47", "2026-08-30",
     ("Added giaitri321.vip Java source, prioritizing 320x240 versions",
      "Thêm nguồn game Java giaitri321.vip, ưu tiên bản 320x240"),
     []),

    ("1.46", "2026-08-30",
     ("Java emulator updates seamlessly via the in-app updater",
      "Bộ giả lập Java đi theo đường cập nhật trong app"),
     []),

    ("1.45", "2026-08-30",
     ("Text input in Java games is now supported",
      "Game Java hỏi nhập chữ giờ chơi được"),
     []),

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
     ("Language switch updates immediately, with no restart",
      "Đổi ngôn ngữ có tác dụng ngay, không cần khởi động lại"),
     []),

    ("1.34", "2026-08-29",
     ("Vietnamese text on downloaded games no longer wraps mid-accent",
      "Chữ tiếng Việt ở danh sách game tải về không còn ngắt dòng giữa dấu"),
     []),

    ("1.33", "2026-08-29",
     ("A failed update cleans up after itself, leaving the running install intact",
      "Bản cập nhật hỏng tự dọn dẹp, bản đang chạy còn nguyên"),
     []),

    ("1.32", "2026-08-29",
     ("Update screen tells you what changed in the new version",
      "Màn hình cập nhật báo bản mới có gì khác"),
     []),
]

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
