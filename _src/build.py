#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render the landing page in both languages from one template.

    python3 _src/build.py

Writes index.html (English, the default) and vi/index.html. Two real pages
rather than a JavaScript toggle: a crawler only ever sees the default language
of a page that swaps its text in the browser, and this site wants both indexed.
Each carries hreflang pointing at the other.

Asset paths are root-absolute so the same markup works from / and from /vi/.
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAIN = "https://retrohub.xuanhoa493.com"
# One place to bump. Four strings drifted apart before this was a constant:
# the two filenames, the release URL and the softwareVersion in the JSON-LD.
VERSION = "1.33"
VER_FULL = "RetroHub-%s-full.zip" % VERSION
VER_LITE = "RetroHub-%s.zip" % VERSION
REL = ("https://github.com/nguyenxuanhoa493/repohubtool/releases/download/v%s"
       % VERSION)

# slug -> (title, description) per language. The slug is also the screenshot
# filename, looked up under shots/<lang>/.
FEATURES = [
    ("kho-game",
     ("Game library", "39,971 titles from several sources, filtered by system and by source"),
     ("Kho game", "39.971 tựa từ nhiều nguồn, lọc theo hệ máy và theo nguồn")),
    ("sftp",
     ("File transfer over Wi-Fi", "Turn on SFTP and copy games across from your computer, no card removal"),
     ("Truyền file qua Wi-Fi", "Bật SFTP là chép game vào máy từ máy tính, không cần rút thẻ nhớ")),
    ("java",
     ("Java J2ME games", "2,713 games in 26 shelves, with key mapping and resolution folders"),
     ("Game Java J2ME", "2.713 game chia 26 nhóm, gán phím và chọn độ phân giải")),
    ("cap-nhat",
     ("Self-updating", "Tells you when a new build is out, downloads only what changed"),
     ("Tự cập nhật", "Báo khi có bản mới, chỉ tải tệp thay đổi")),
    ("ket-noi",
     ("Other connections", "SSH, ADB, MTP and screen streaming to a browser"),
     ("Kết nối khác", "SSH, ADB, MTP và stream màn hình ra trình duyệt")),
]

OS_ROWS = [
    ("ok",
     ("TrimUI Brick — stock OS", "Tested directly, every feature works"),
     ("TrimUI Brick — hệ gốc", "Đã thử trực tiếp, chạy đầy đủ mọi tính năng")),
    ("ok",
     ("TrimUI Brick Pro — stock OS", "Tested directly on firmware 1.1.1; Python ships with the app"),
     ("TrimUI Brick Pro — hệ gốc", "Đã thử trực tiếp trên firmware 1.1.1; Python đóng gói sẵn trong app")),
    ("wait",
     ("TrimUI Smart Pro — stock OS", "Same firmware family, likely fine but untested"),
     ("TrimUI Smart Pro — hệ gốc", "Cùng dòng firmware, nhiều khả năng chạy được nhưng chưa thử")),
    ("wait",
     ("CrossMix, Knulli and other CFW", "Untested. If it runs for you, tell me in the chat group"),
     ("CrossMix, Knulli và các bản CFW", "Chưa thử. Nếu bạn chạy được, báo tôi trong nhóm chat")),
]

ROADMAP = [
    ("done", "ok",
     ("Game library and core tools", "Done",
      "Nearly 40,000 games, Java J2ME emulator, Wi-Fi file transfer, self-updating"),
     ("Kho game và tiện ích cơ bản", "Đã xong",
      "Gần 40.000 game, giả lập Java J2ME, truyền file qua Wi-Fi, tự động cập nhật")),
    ("", "next",
     ("More systems and firmware", "Up next",
      "Reaching the CFW builds and other handhelds"),
     ("Hỗ trợ thêm hệ điều hành và máy khác", "Đang tới",
      "Mở rộng ra các bản CFW và những dòng máy cầm tay khác")),
    ("", "next",
     ("Online app store", "Planned",
      "Install more tools straight from the device, no card removal"),
     ("Kho ứng dụng online", "Dự kiến",
      "Cài thêm tiện ích ngay trên máy, không cần rút thẻ nhớ")),
    ("", "next",
     ("Online matchmaking server", "Planned",
      "Find other players and play together over the network"),
     ("Máy chủ ghép trận online", "Dự kiến",
      "Tìm người chơi và đấu cùng nhau qua mạng")),
]

T = {
 "en": {
  "lang": "en", "other": "vi", "other_name": "Tiếng Việt", "home": "/",
  "title": "RetroHub — Games and tools for handheld consoles",
  "desc": "RetroHub: nearly 40,000 games, a Java J2ME emulator, Wi-Fi file transfer and self-updating for TrimUI handheld consoles. Install once, update forever.",
  "keywords": "RetroHub, TrimUI Brick, handheld console, game library, ROM, emulator, J2ME, Java games, retro handheld",
  "og_alt": "RetroHub — games and tools for handheld consoles",
  "og_desc": "Nearly 40,000 games, a Java J2ME emulator, Wi-Fi file transfer and self-updating. Install once, update forever.",
  "tagline": "Games and tools for handheld consoles",
  "nav": ["Features", "Install", "Download", "Support", "Roadmap", "Contact"],
  "dls": "downloads so far",
  "dl_full": "Download full", "dl_full_sub": "93 MB · Java emulator included",
  "dl_lite": "Download lite", "dl_lite_sub": "30 MB · no Java emulator",
  "h_feat": "Highlights", "h_install": "How to install", "h_dl": "Download",
  "h_support": "Support me", "h_road": "Roadmap", "h_contact": "Contact",
  "steps": ["Unzip what you downloaded — you will see a <code>RetroHub</code> folder.",
            "Put the memory card in your computer and copy that whole folder into <code>/Apps/</code> on the card.",
            "Put the card back, open <b>Apps → RetroHub</b>."],
  "note": "You only do this once. From then on the app checks for a new build every time it opens and downloads only what changed — usually a few hundred KB.",
  "full_t": "Full", "full_s": "93 MB",
  "full_p": "The app, 39,971 games and the Java J2ME emulator. Pick this if you want to play Java games.",
  "lite_t": "Lite", "lite_s": "30 MB",
  "lite_p": "The app and the game library, without the Java emulator. Quick to install, you can add Java later.",
  "h_os": "Supported systems",
  "sup_p": "RetroHub is a personal project, built and given away for free. If it is useful to you, a coffee keeps me going.",
  "bank": "Bank", "holder": "Account holder", "acct": "Account number",
  "bmc": "Buy me a coffee", "bmc_sub": "Card and PayPal",
  "bank_hdr": "Bank transfer (Vietnam)",
  "who_role": "RetroHub author",
  "who_p": "Questions, bug reports and ideas go in the chat group — I read and answer there. For anything private, use one of the ways below.",
  "join": "Join the Telegram group",
  "c_tg": "Telegram", "c_mail": "Email", "c_tel": "Phone",
  "disc_h": "Disclaimer",
  "disc": ["<b>RetroHub is a search and download tool. It stores no game files.</b> The app only points at sources that are already public on the internet.",
           "Every game is copyright its original developer. We claim no ownership of any title.",
           "This is a non-profit project, made to preserve gaming heritage and serve nostalgia.",
           'If you own the copyright to a title and want it removed from the index, <a href="mailto:nguyenxuanhoa493@gmail.com">get in touch</a> — I will take it down.'],
 },
 "vi": {
  "lang": "vi", "other": "en", "other_name": "English", "home": "/vi/",
  "title": "RetroHub — Kho game và tiện ích cho máy chơi game cầm tay",
  "desc": "RetroHub: kho gần 40.000 game, giả lập Java J2ME, truyền file qua Wi-Fi và tự động cập nhật cho máy chơi game cầm tay TrimUI. Cài một lần, tự cập nhật mãi.",
  "keywords": "RetroHub, TrimUI Brick, máy chơi game cầm tay, kho game, ROM, giả lập, J2ME, game Java, retro handheld",
  "og_alt": "RetroHub — kho game và tiện ích cho máy chơi game cầm tay",
  "og_desc": "Gần 40.000 game, giả lập Java J2ME, truyền file qua Wi-Fi và tự động cập nhật. Cài một lần, tự cập nhật mãi.",
  "tagline": "Kho game và tiện ích cho máy chơi game cầm tay",
  "nav": ["Tính năng", "Cách cài", "Tải về", "Ủng hộ", "Lộ trình", "Liên hệ"],
  "dls": "lượt tải",
  "dl_full": "Tải bản đầy đủ", "dl_full_sub": "93 MB · kèm giả lập Java",
  "dl_lite": "Tải bản gọn", "dl_lite_sub": "30 MB · không kèm Java",
  "h_feat": "Tính năng nổi bật", "h_install": "Cách cài", "h_dl": "Tải về",
  "h_support": "Ủng hộ tôi", "h_road": "Lộ trình phát triển", "h_contact": "Liên hệ",
  "steps": ["Giải nén tệp vừa tải, bạn sẽ thấy thư mục <code>RetroHub</code>.",
            "Cắm thẻ nhớ vào máy tính, chép cả thư mục đó vào <code>/Apps/</code> trên thẻ.",
            "Lắp thẻ lại vào máy, mở <b>Apps → RetroHub</b>."],
  "note": "Chỉ cần cài tay đúng một lần. Từ đó ứng dụng tự kiểm tra bản mới mỗi lần mở và chỉ tải phần thay đổi — thường vài trăm KB.",
  "full_t": "Bản đầy đủ", "full_s": "93 MB",
  "full_p": "Ứng dụng, kho 39.971 game và bộ giả lập Java J2ME. Chọn bản này nếu bạn muốn chơi game Java.",
  "lite_t": "Bản gọn", "lite_s": "30 MB",
  "lite_p": "Ứng dụng và kho game, không kèm giả lập Java. Cài nhanh, thêm phần Java sau cũng được.",
  "h_os": "Hệ điều hành hỗ trợ",
  "sup_p": "RetroHub là dự án cá nhân, làm và phát hành miễn phí. Nếu nó có ích cho bạn, một ly cà phê cũng là động lực để tôi làm tiếp.",
  "bank": "Ngân hàng", "holder": "Chủ tài khoản", "acct": "Số tài khoản",
  "bmc": "Mời tôi ly cà phê", "bmc_sub": "Thẻ quốc tế và PayPal",
  "bank_hdr": "Chuyển khoản trong nước",
  "who_role": "Tác giả RetroHub",
  "who_p": "Hỏi đáp, báo lỗi và góp ý xin gửi vào nhóm chat — tôi đọc và trả lời ở đó. Cần trao đổi riêng thì dùng một trong các cách bên dưới.",
  "join": "Vào nhóm Telegram",
  "c_tg": "Telegram riêng", "c_mail": "Email", "c_tel": "Điện thoại",
  "disc_h": "Tuyên bố miễn trừ trách nhiệm",
  "disc": ["<b>RetroHub là công cụ tra cứu và tải game, không lưu trữ bất kỳ tệp game nào.</b> Ứng dụng chỉ dẫn tới những nguồn vốn đã công khai trên Internet.",
           "Mọi tựa game đều thuộc bản quyền của nhà phát triển gốc. Chúng tôi không sở hữu và không tuyên bố quyền sở hữu với bất kỳ tựa game nào.",
           "Đây là dự án phi lợi nhuận, làm ra để lưu giữ di sản văn hoá game và phục vụ nhu cầu hoài niệm.",
           'Nếu bạn là chủ sở hữu bản quyền và muốn gỡ một tựa game khỏi danh mục, <a href="mailto:nguyenxuanhoa493@gmail.com">hãy liên hệ với tôi</a> — tôi sẽ gỡ ngay.'],
 },
}

IDS = ["tinh-nang", "cach-cai", "tai-ve", "ung-ho", "lo-trinh", "lien-he"]

SVG_TG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21.9 4.3 18.7 20c-.2 1-.9 1.3-1.8.8l-4.9-3.6-2.4 2.3c-.3.3-.5.5-1 .5l.4-5 9.1-8.2c.4-.4-.1-.6-.6-.2L6.3 13.1l-4.8-1.5c-1-.3-1-1 .2-1.5l18.8-7.3c.9-.3 1.6.2 1.4 1.5z"/></svg>'
SVG_MAIL = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 5h18a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1zm9 7.2 8-4.7V6.5l-8 4.7-8-4.7v1L12 12.2z"/></svg>'
SVG_TEL = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6.6 10.8a15.5 15.5 0 0 0 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.2.4 2.4.6 3.6.6.6 0 1 .5 1 1V20c0 .6-.4 1-1 1A17 17 0 0 1 3 4c0-.6.5-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.4 0 .8-.2 1l-2.3 2.2z"/></svg>'
SVG_DL = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a1 1 0 0 1 1 1v8.6l3.3-3.3a1 1 0 1 1 1.4 1.4l-5 5a1 1 0 0 1-1.4 0l-5-5a1 1 0 1 1 1.4-1.4l3.3 3.3V4a1 1 0 0 1 1-1zM4 18a1 1 0 0 1 1 1v1h14v-1a1 1 0 1 1 2 0v2a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-2a1 1 0 0 1 1-1z"/></svg>'
SVG_CUP = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h13v3h2.5A2.5 2.5 0 0 1 22 9.5v1A3.5 3.5 0 0 1 18.5 14H17v1a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5V4zm13 5v3h1.5A1.5 1.5 0 0 0 20 10.5v-1A.5.5 0 0 0 19.5 9H17zM3 21h15v2H3v-2z"/></svg>'


CSS = """
  :root{
    --bg:#0d1220; --panel:#16223a; --line:#2b3d5e;
    --accent:#00f6f6; --accent-dim:#0a8f96;
    --text:#eef3fb; --muted:#93a4c0; --gold:#ffcf3c; --green:#3ddc97;
  }
  *{box-sizing:border-box}
  html{scroll-behavior:smooth;scroll-padding-top:74px}
  body{margin:0;background:var(--bg);color:var(--text);
    font:16px/1.65 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
  .wrap{max-width:1080px;margin:0 auto;padding:0 22px}

  nav{position:sticky;top:0;z-index:50;background:rgba(13,18,32,.86);
    backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
  .navin{display:flex;align-items:center;gap:16px;height:58px;
    max-width:1080px;margin:0 auto;padding:0 22px}
  .brand{display:flex;align-items:center;gap:9px;font-weight:800;
    text-decoration:none;color:var(--text);letter-spacing:-.2px;flex:none}
  .brand img{width:26px;height:26px}
  .navlinks{display:flex;gap:4px;margin-left:auto;overflow-x:auto;scrollbar-width:none}
  .navlinks::-webkit-scrollbar{display:none}
  .navlinks a{color:var(--muted);text-decoration:none;font-size:.93rem;
    padding:7px 12px;border-radius:8px;white-space:nowrap;transition:color .15s,background .15s}
  .navlinks a:hover{color:var(--text);background:#1b2c49}
  .navlinks a.here{color:var(--accent);background:#14243d}
  /* Language switch shows the flag of the language you would move to, so the
     button says what it does rather than what you already have. */
  .lang{display:flex;align-items:center;gap:8px;flex:none;margin-left:10px;
    padding:6px 12px 6px 8px;border:1px solid var(--line);border-radius:999px;
    text-decoration:none;color:var(--muted);font-size:.88rem;
    transition:border-color .15s,color .15s,background .15s}
  .lang:hover{border-color:var(--accent-dim);color:var(--text);background:#14243d}
  .lang img{width:24px;height:16px;border-radius:3px;display:block}

  header{padding:70px 0 52px;text-align:center;
    background:radial-gradient(900px 400px at 50% -140px,rgba(0,246,246,.16),transparent)}
  .logo{width:118px;height:118px;display:block;margin:0 auto;
    filter:drop-shadow(0 6px 22px rgba(0,246,246,.28));animation:float 5s ease-in-out infinite}
  @keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-9px)}}
  h1{font-size:clamp(2.1rem,5.6vw,3rem);margin:18px 0 8px;letter-spacing:-.6px}
  .sub{color:var(--muted);font-size:1.12rem;margin:0 0 28px}

  .cta{display:flex;gap:12px;flex-wrap:wrap;justify-content:center}
  .btn{position:relative;display:inline-block;text-align:center;text-decoration:none;
    font-weight:700;padding:14px 24px;border-radius:10px;background:var(--accent);
    color:#04121b;transition:transform .18s cubic-bezier(.2,.8,.3,1),box-shadow .18s,filter .18s}
  .btn:hover{transform:translateY(-3px);filter:brightness(1.1);
    box-shadow:0 12px 26px rgba(0,246,246,.3)}
  .btn:active{transform:translateY(-1px)}
  .btn.ghost{background:transparent;color:var(--accent);border:1px solid var(--accent-dim)}
  .btn.ghost:hover{background:rgba(0,246,246,.08);box-shadow:0 12px 26px rgba(0,246,246,.14)}
  .btn small{display:block;font-weight:500;font-size:.78rem;opacity:.72;margin-top:2px}

  /* A pill rather than a line of text: it sits under two large buttons and had
     to read as a badge, not as leftover caption. */
  .dlcount{display:inline-flex;align-items:center;gap:9px;margin:24px 0 0;
    padding:8px 18px 8px 14px;border-radius:999px;
    background:linear-gradient(180deg,#16233c,#121c31);
    border:1px solid var(--line);box-shadow:0 6px 18px rgba(0,0,0,.35);
    animation:pop .45s cubic-bezier(.2,.9,.3,1.2)}
  .dlcount svg{width:17px;height:17px;fill:var(--accent);flex:none;
    filter:drop-shadow(0 0 6px rgba(0,246,246,.5))}
  .dlcount b{color:var(--accent);font-size:1.12rem;font-variant-numeric:tabular-nums;
    letter-spacing:.2px}
  .dlcount span{color:var(--muted);font-size:.88rem}
  @keyframes pop{from{opacity:0;transform:translateY(8px) scale(.96)}
                 to{opacity:1;transform:none}}

  h2{font-size:1.4rem;margin:0 0 18px;padding-bottom:10px;border-bottom:1px solid var(--line)}
  section{padding:52px 0 0}
  main{padding-bottom:64px}
  ol{padding-left:22px} ol li{margin:12px 0}
  code{background:#0a1120;border:1px solid var(--line);border-radius:6px;
    padding:2px 7px;font-size:.9em;color:var(--accent);white-space:nowrap}
  .note{background:rgba(255,207,60,.08);border:1px solid rgba(255,207,60,.35);
    border-radius:10px;padding:14px 18px;color:#f4e3b8;font-size:.94rem}

  .show{display:grid;gap:26px;grid-template-columns:340px 1fr;align-items:start}
  .tabs{list-style:none;margin:0;padding:0;display:grid;gap:8px}
  .tab{position:relative;overflow:hidden;background:var(--panel);
    border:1px solid var(--line);border-radius:10px;padding:13px 16px;
    cursor:pointer;transition:border-color .15s,background .15s,transform .15s}
  .tab:hover{border-color:var(--accent-dim);transform:translateX(3px)}
  .tab[aria-selected="true"]{border-color:var(--accent);background:#1b2c49}
  .tab b{display:block;color:var(--accent);font-size:.95rem}
  .tab span{color:var(--muted);font-size:.87rem;line-height:1.45;display:block;margin-top:2px}
  .bar{position:absolute;left:0;bottom:0;height:3px;width:0;background:var(--accent)}
  .stage{position:relative;border:1px solid var(--line);border-radius:14px;
    overflow:hidden;background:#0a1120;aspect-ratio:4/3}
  .stage img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;
    opacity:0;transform:scale(1.015);transition:opacity .45s ease,transform .45s ease}
  .stage img.on{opacity:1;transform:scale(1)}

  .dl{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(270px,1fr))}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:22px;
    display:flex;flex-direction:column;transition:transform .18s,border-color .18s}
  .card:hover{transform:translateY(-4px);border-color:var(--accent-dim)}
  .card.main{border-color:var(--accent-dim)}
  .card h3{margin:0 0 4px;font-size:1.1rem}
  .size{color:var(--gold);font-weight:600;font-size:.9rem}
  .card p{color:var(--muted);font-size:.94rem;margin:12px 0 20px;flex:1}
  .card .btn{display:block}

  .os{list-style:none;padding:0;margin:20px 0 0;display:grid;gap:10px;
    grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
  .os li{background:var(--panel);border:1px solid var(--line);border-radius:10px;
    padding:13px 16px;font-size:.94rem;display:flex;gap:11px;align-items:flex-start}
  .dot{width:10px;height:10px;border-radius:50%;margin-top:7px;flex:none}
  .dot.ok{background:var(--green);box-shadow:0 0 10px rgba(61,220,151,.6)}
  .dot.wait{background:#5d6f8e}
  .os b{display:block} .os span{color:var(--muted);font-size:.87rem}

  .road{list-style:none;padding:0;margin:0;position:relative}
  .road::before{content:"";position:absolute;left:11px;top:10px;bottom:10px;
    width:2px;background:var(--line)}
  .road li{position:relative;padding:0 0 22px 42px}
  .road li:last-child{padding-bottom:0}
  .pin{position:absolute;left:2px;top:3px;width:20px;height:20px;border-radius:50%;
    background:var(--bg);border:2px solid var(--line)}
  .road li.done .pin{border-color:var(--green);background:var(--green);
    box-shadow:0 0 12px rgba(61,220,151,.5)}
  .road b{display:block;font-size:1.02rem} .road span{color:var(--muted);font-size:.9rem}
  .badge{display:inline-block;font-size:.75rem;font-weight:700;border-radius:999px;
    padding:2px 10px;margin-left:8px;vertical-align:2px}
  .badge.ok{background:rgba(61,220,151,.16);color:var(--green);border:1px solid rgba(61,220,151,.45)}
  .badge.next{background:#1b2c49;color:var(--muted);border:1px solid var(--line)}

  .donate{display:grid;gap:26px;align-items:start;grid-template-columns:220px 1fr;
    background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:24px}
  .qr{width:220px;height:220px;background:#fff;border-radius:10px;padding:10px;display:block}
  .bankhdr{color:var(--muted);font-size:.8rem;text-transform:uppercase;
    letter-spacing:.06em;margin:0 0 4px}
  .rows{margin:0;display:grid;gap:2px}
  .rows div{display:flex;justify-content:space-between;gap:16px;
    padding:9px 0;border-bottom:1px solid var(--line)}
  .rows div:last-child{border-bottom:0}
  .rows dt{color:var(--muted);font-size:.92rem}
  .rows dd{margin:0;font-weight:600}
  .bmc{display:inline-flex;align-items:center;gap:10px;margin-top:18px;
    background:var(--gold);color:#1a1200}
  .bmc:hover{box-shadow:0 12px 26px rgba(255,207,60,.28)}
  .bmc svg{width:20px;height:20px;fill:currentColor;flex:none}

  .who{display:grid;gap:26px;grid-template-columns:132px 1fr;align-items:start;
    background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:26px}
  .ava{width:132px;height:132px;border-radius:50%;background:#0a1120;
    border:1px solid var(--line);padding:14px}
  .whoin b{display:block;font-size:1.25rem;letter-spacing:-.2px}
  .whoin > span{color:var(--accent);font-size:.9rem}
  .whoin p{color:var(--muted);font-size:.95rem;margin:14px 0 18px}
  .joinbtn{display:inline-flex;align-items:center;gap:9px}
  .joinbtn svg{width:19px;height:19px;fill:currentColor}
  .chips{list-style:none;margin:20px 0 0;padding:0;display:grid;gap:10px;
    grid-template-columns:repeat(auto-fit,minmax(230px,1fr))}
  .chips a{display:flex;align-items:center;gap:12px;text-decoration:none;
    background:#0f1a2e;border:1px solid var(--line);border-radius:10px;
    padding:11px 14px;color:var(--text);
    transition:border-color .15s,transform .15s,background .15s}
  .chips a:hover{border-color:var(--accent-dim);background:#14243d;transform:translateY(-2px)}
  .chips svg{width:20px;height:20px;fill:var(--accent);flex:none}
  .chips span{display:block;min-width:0;font-size:.94rem;overflow:hidden;
    text-overflow:ellipsis;white-space:nowrap}
  .chips i{display:block;font-style:normal;color:var(--muted);font-size:.78rem}

  .disc{border-left:3px solid var(--accent-dim);background:#111b2e;
    border-radius:0 12px 12px 0;padding:20px 24px}
  .disc p{color:var(--muted);font-size:.92rem;margin:0 0 10px;line-height:1.6}
  .disc p:last-child{margin-bottom:0}
  .disc b{color:var(--text)}
  .disc a{color:var(--accent);text-decoration:none}
  .disc a:hover{text-decoration:underline}

  .rise{opacity:0;transform:translateY(22px);
    transition:opacity .6s ease,transform .6s cubic-bezier(.2,.8,.3,1)}
  .rise.seen{opacity:1;transform:none}

  @media (max-width:860px){
    .show{grid-template-columns:1fr}
    .donate{grid-template-columns:1fr;justify-items:center;text-align:center}
    .who{grid-template-columns:1fr;justify-items:center;text-align:center}
    .chips a{text-align:left}
    .rows div{justify-content:center;flex-direction:column;gap:0;text-align:center}
    .brand span{display:none}
  }
  @media (prefers-reduced-motion:reduce){
    html{scroll-behavior:auto}
    .logo{animation:none}
    .rise{opacity:1;transform:none;transition:none}
    .stage img{transition:none;transform:none}
    .btn:hover,.card:hover,.tab:hover,.chips a:hover{transform:none}
  }
"""


JS = """
(function () {
  var HOLD = 5000, SHOTS = "__SHOTDIR__";
  var FEATURES = __FEATJSON__;
  var tabs = document.getElementById("tabs"), stage = document.getElementById("stage");
  var bars = [], imgs = [], at = 0, timer = null;

  FEATURES.forEach(function (f, i) {
    var li = document.createElement("li");
    li.className = "tab";
    li.setAttribute("role", "tab");
    li.setAttribute("aria-selected", i === 0 ? "true" : "false");
    li.innerHTML = '<b></b><span></span><i class="bar"></i>';
    li.querySelector("b").textContent = f[1];
    li.querySelector("span").textContent = f[2];
    li.addEventListener("click", function () { show(i, true); });
    tabs.appendChild(li);
    bars.push(li.querySelector(".bar"));

    var img = document.createElement("img");
    img.src = SHOTS + f[0] + ".png";
    img.alt = f[1];
    img.loading = i === 0 ? "eager" : "lazy";
    if (i === 0) img.className = "on";
    stage.appendChild(img);
    imgs.push(img);
  });

  function paint() {
    for (var i = 0; i < FEATURES.length; i++) {
      var sel = i === at;
      tabs.children[i].setAttribute("aria-selected", sel ? "true" : "false");
      imgs[i].className = sel ? "on" : "";
      var b = bars[i];
      b.style.transition = "none";
      b.style.width = "0%";
      if (sel) { void b.offsetWidth;
        b.style.transition = "width " + HOLD + "ms linear";
        b.style.width = "100%"; }
    }
  }
  function show(i, manual) { at = (i + FEATURES.length) % FEATURES.length; paint(); if (manual) start(); }
  function start() { clearInterval(timer); timer = setInterval(function () { show(at + 1); }, HOLD); }
  function stop() { clearInterval(timer); }

  paint(); start();
  var box = document.querySelector(".show");
  box.addEventListener("mouseenter", stop);
  box.addEventListener("mouseleave", start);
  document.addEventListener("visibilitychange", function () { document.hidden ? stop() : start(); });

  // Download totals come from the GitHub Releases API, which already counts
  // every asset download and allows browser requests. No server of our own.
  // Unauthenticated callers get 60 requests an hour per IP, so the answer is
  // kept for the session - a visitor who reloads should not burn the budget of
  // everyone behind the same office or carrier NAT.
  (function () {
    var box = document.getElementById("dlcount");
    if (!box) return;
    function put(n) {
      if (!n) return;                       // nothing to boast about yet
      var out = box.querySelector("b");
      box.hidden = false;
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        out.textContent = n.toLocaleString();
        return;
      }
      // Count up on reveal. Eased so it slows into the final figure instead of
      // stopping dead, which reads as the number still loading.
      var t0 = 0, DUR = 900;
      requestAnimationFrame(function step(t) {
        if (!t0) t0 = t;
        var k = Math.min(1, (t - t0) / DUR);
        out.textContent = Math.round(n * (1 - Math.pow(1 - k, 3))).toLocaleString();
        if (k < 1) requestAnimationFrame(step);
      });
    }
    var cached = null;
    try { cached = sessionStorage.getItem("rh_dl"); } catch (e) {}
    if (cached) { put(parseInt(cached, 10)); return; }
    fetch("https://api.github.com/repos/nguyenxuanhoa493/repohubtool/releases")
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (rs) {
        if (!rs) return;
        var n = 0;
        rs.forEach(function (rel) {
          (rel.assets || []).forEach(function (a) { n += a.download_count || 0; });
        });
        try { sessionStorage.setItem("rh_dl", String(n)); } catch (e) {}
        put(n);
      })
      .catch(function () { /* stays hidden, which is better than a broken line */ });
  })();

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var secs = [].slice.call(document.querySelectorAll("section[id]"));
  if ("IntersectionObserver" in window && !reduce) {
    var rev = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("seen"); rev.unobserve(e.target); } });
    }, { rootMargin: "0px 0px -12% 0px" });
    [].forEach.call(document.querySelectorAll(".rise"), function (el) { rev.observe(el); });
  } else {
    [].forEach.call(document.querySelectorAll(".rise"), function (el) { el.classList.add("seen"); });
  }
  if ("IntersectionObserver" in window) {
    var links = {};
    [].forEach.call(document.querySelectorAll(".navlinks a"), function (a) {
      links[a.getAttribute("href").slice(1)] = a; });
    var visible = {};
    var spy = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (e.isIntersecting) visible[e.target.id] = 1; else delete visible[e.target.id];
      });
      var cur = null;
      for (var i = 0; i < secs.length; i++) { if (visible[secs[i].id]) { cur = secs[i].id; break; } }
      Object.keys(links).forEach(function (k) { links[k].classList.toggle("here", k === cur); });
    }, { rootMargin: "-58px 0px -62% 0px" });
    secs.forEach(function (el) { spy.observe(el); });
  }
})();
"""

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
<link rel="alternate" hreflang="en" href="{DOMAIN}/">
<link rel="alternate" hreflang="vi" href="{DOMAIN}/vi/">
<link rel="alternate" hreflang="x-default" href="{DOMAIN}/">
<link rel="icon" href="/logo.png">
<link rel="apple-touch-icon" href="/logo.png">
<meta property="og:type" content="website">
<meta property="og:locale" content="{oglocale}">
<meta property="og:site_name" content="RetroHub">
<meta property="og:url" content="{canon}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{og_desc}">
<meta property="og:image" content="{DOMAIN}/og-{lang}.png">
<meta property="og:image:secure_url" content="{DOMAIN}/og-{lang}.png">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{og_alt}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{og_desc}">
<meta name="twitter:image" content="{DOMAIN}/og-{lang}.png">
<meta name="twitter:image:alt" content="{og_alt}">
<script type="application/ld+json">
{ldjson}
</script>
<style>{css}</style>
</head>
<body>

<nav>
  <div class="navin">
    <a class="brand" href="{home}"><img src="/logo.png" alt=""><span>RetroHub</span></a>
    <div class="navlinks">{navlinks}</div>
    <a class="lang" href="{otherhome}" hreflang="{other}" title="{other_name}">
      <img src="/files/assets/flag_{other}.png" alt=""><span>{other_name}</span></a>
  </div>
</nav>

<header id="top">
  <div class="wrap">
    <img class="logo" src="/logo.png" alt="RetroHub">
    <h1>RetroHub</h1>
    <p class="sub">{tagline}</p>
    <div class="cta">
      <a class="btn" href="{REL}/{VER_FULL}">{dl_full}<small>{dl_full_sub}</small></a>
      <a class="btn ghost" href="{REL}/{VER_LITE}">{dl_lite}<small>{dl_lite_sub}</small></a>
    </div>
    <p class="dlcount" id="dlcount" hidden>{SVG_DL}<b>0</b><span>{dls}</span></p>
  </div>
</header>

<main class="wrap">
  <section id="tinh-nang" class="rise">
    <h2>{h_feat}</h2>
    <div class="show">
      <ul class="tabs" id="tabs" role="tablist"></ul>
      <div class="stage" id="stage"></div>
    </div>
  </section>

  <section id="cach-cai" class="rise">
    <h2>{h_install}</h2>
    <ol>{steps}</ol>
    <p class="note">{note}</p>
  </section>

  <section id="tai-ve" class="rise">
    <h2>{h_dl}</h2>
    <div class="dl">
      <div class="card main">
        <h3>{full_t}</h3><span class="size">{full_s}</span>
        <p>{full_p}</p>
        <a class="btn" href="{REL}/{VER_FULL}">{dl_full}</a>
      </div>
      <div class="card">
        <h3>{lite_t}</h3><span class="size">{lite_s}</span>
        <p>{lite_p}</p>
        <a class="btn ghost" href="{REL}/{VER_LITE}">{dl_lite}</a>
      </div>
    </div>
    <h3 style="margin:34px 0 0;font-size:1.05rem">{h_os}</h3>
    <ul class="os">{osrows}</ul>
  </section>

  <section id="ung-ho" class="rise">
    <h2>{h_support}</h2>
    <div class="donate">
      <img class="qr" src="/files/assets/qr_donate.png" alt="QR Techcombank">
      <div>
        <p style="margin-top:0">{sup_p}</p>
        <p class="bankhdr">{bank_hdr}</p>
        <dl class="rows">
          <div><dt>{bank}</dt><dd>Techcombank</dd></div>
          <div><dt>{holder}</dt><dd>NGUYEN XUAN HOA</dd></div>
          <div><dt>{acct}</dt><dd>1732 8888 88</dd></div>
        </dl>
        <a class="btn bmc" href="https://buymeacoffee.com/xuanhoa493">{SVG_CUP}
          <span>{bmc}<small>{bmc_sub}</small></span></a>
      </div>
    </div>
  </section>

  <section id="lo-trinh" class="rise">
    <h2>{h_road}</h2>
    <ul class="road">{roadrows}</ul>
  </section>

  <section id="lien-he" class="rise">
    <h2>{h_contact}</h2>
    <div class="who">
      <img class="ava" src="/logo.png" alt="">
      <div class="whoin">
        <b>Nguyễn Xuân Hòa</b>
        <span>{who_role}</span>
        <p>{who_p}</p>
        <a class="btn joinbtn" href="https://t.me/retrohubtool">{SVG_TG} {join}</a>
        <ul class="chips">
          <li><a href="https://t.me/xuanhoa493">{SVG_TG}
            <span><i>{c_tg}</i>@xuanhoa493</span></a></li>
          <li><a href="mailto:nguyenxuanhoa493@gmail.com">{SVG_MAIL}
            <span><i>{c_mail}</i>nguyenxuanhoa493@gmail.com</span></a></li>
          <li><a href="tel:+84962369231">{SVG_TEL}
            <span><i>{c_tel}</i>0962 369 231</span></a></li>
        </ul>
      </div>
    </div>
  </section>

  <section class="rise">
    <div class="disc">
      <h2 style="border:0;padding:0;margin:0 0 12px;font-size:1.1rem">{disc_h}</h2>
      {disc}
    </div>
  </section>
</main>

<script>{js}</script>
</body>
</html>
"""


def render(lang):
    t = T[lang]
    canon = DOMAIN + ("/" if lang == "en" else "/vi/")
    other = t["other"]
    feats = [[slug, (en if lang == "en" else vi)[0], (en if lang == "en" else vi)[1]]
             for slug, en, vi in FEATURES]

    ld = {
        "@context": "https://schema.org", "@type": "SoftwareApplication",
        "name": "RetroHub", "applicationCategory": "GameApplication",
        "operatingSystem": "TrimUI (Linux)", "url": canon,
        "downloadUrl": "https://github.com/nguyenxuanhoa493/repohubtool/releases/latest",
        "softwareVersion": VERSION, "inLanguage": lang, "description": t["desc"],
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "VND"},
        "author": {"@type": "Person", "name": "Nguyễn Xuân Hòa",
                   "url": "https://xuanhoa493.com"},
    }

    navlinks = "".join('<a href="#%s">%s</a>' % (i, n) for i, n in zip(IDS, t["nav"]))
    steps = "".join("<li>%s</li>" % s for s in t["steps"])
    osrows = "".join(
        '<li><span class="dot %s"></span><div><b>%s</b><span>%s</span></div></li>'
        % (kind, (en if lang == "en" else vi)[0], (en if lang == "en" else vi)[1])
        for kind, en, vi in OS_ROWS)
    roadrows = "".join(
        '<li class="%s"><span class="pin"></span><b>%s<span class="badge %s">%s</span></b>'
        '<span>%s</span></li>'
        % (done, (en if lang == "en" else vi)[0], bk, (en if lang == "en" else vi)[1],
           (en if lang == "en" else vi)[2])
        for done, bk, en, vi in ROADMAP)
    disc = "".join("<p>%s</p>" % p for p in t["disc"])

    js = (JS.replace("__SHOTDIR__", "/shots/%s/" % lang)
            .replace("__FEATJSON__", json.dumps(feats, ensure_ascii=False)))

    out = PAGE
    for k, v in {
        "lang": lang, "title": t["title"], "desc": t["desc"], "keywords": t["keywords"],
        "canon": canon, "DOMAIN": DOMAIN, "oglocale": "en_US" if lang == "en" else "vi_VN",
        "og_desc": t["og_desc"], "ldjson": json.dumps(ld, ensure_ascii=False, indent=2),
        "css": CSS, "home": t["home"], "otherhome": T[other]["home"],
        "other": other, "other_name": t["other_name"], "navlinks": navlinks,
        "tagline": t["tagline"], "REL": REL, "VER_FULL": VER_FULL, "VER_LITE": VER_LITE,
        "steps": steps, "osrows": osrows, "roadrows": roadrows, "disc": disc,
        "SVG_TG": SVG_TG, "SVG_MAIL": SVG_MAIL, "SVG_TEL": SVG_TEL, "SVG_CUP": SVG_CUP,
        "SVG_DL": SVG_DL,
        "js": js,
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
        path = os.path.join(ROOT, "index.html" if lang == "en" else "vi/index.html")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(render(lang))
        print("  %-16s %6d byte" % (os.path.relpath(path, ROOT), os.path.getsize(path)))


if __name__ == "__main__":
    main()
