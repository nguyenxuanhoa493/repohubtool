#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render the beginner setup guide in both languages.

    python3 _src/build_guide.py

Writes guide/index.html (English) and vi/guide/index.html (Vietnamese), sharing
build.py's CSS, navigation menu, and release constants so the site maintains
one unified visual identity.
"""

import json
import os
import re

from build import (
    ROOT, CSS, DOMAIN, navlinks_for, VERSION, FULL_VERSION,
    VER_FULL, VER_NEXTUI, VER_SD_FULL, SD_FULL_URL, REL
)

SECTIONS = [
    ("quy-trinh", "3-Step Setup", "Quy trình 3 bước"),
    ("cai-le", "Existing SD card?", "Dành cho thẻ cũ"),
    ("faq", "FAQ & Help", "Hỏi đáp & Lỗi"),
]

EXTRA_CSS = """
  .guide-hero{padding:48px 0 28px;text-align:center}
  .badge-hero{display:inline-flex;align-items:center;gap:8px;padding:6px 16px;border-radius:999px;
    background:rgba(0,246,246,.1);border:1px solid var(--accent-dim);color:var(--accent);
    font-size:.82rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;margin-bottom:16px}
  .guide-meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:28px 0 10px}
  .meta-card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:15px 18px;text-align:left}
  .meta-card b{display:block;color:var(--accent);font-size:.88rem;margin-bottom:4px;letter-spacing:.02em}
  .meta-card span{color:var(--muted);font-size:.86rem;line-height:1.45;display:block}

  .toc-nav{margin:24px 0 36px;display:flex;flex-wrap:wrap;gap:8px;justify-content:center;list-style:none;padding:0}
  .toc-nav a{display:inline-block;background:var(--panel);border:1px solid var(--line);
    border-radius:999px;padding:7px 15px;color:var(--muted);text-decoration:none;font-size:.88rem;
    transition:border-color .15s,color .15s,background .15s}
  .toc-nav a:hover{border-color:var(--accent-dim);color:var(--text);background:#14243d}

  .step-box{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:28px;position:relative}
  .step-hdr{display:flex;align-items:center;gap:16px;margin-bottom:20px;flex-wrap:wrap}
  .step-badge{width:46px;height:46px;border-radius:12px;background:linear-gradient(135deg,#0a8f96,#00f6f6);
    color:#04121b;font-weight:800;font-size:1.35rem;display:flex;align-items:center;justify-content:center;flex:none;
    box-shadow:0 0 18px rgba(0,246,246,.3)}
  .step-badge.alt{background:linear-gradient(135deg,#d4a017,#ffcf3c);box-shadow:0 0 18px rgba(255,207,60,.3)}
  .step-badge.done{background:linear-gradient(135deg,#1f9d68,#3ddc97);box-shadow:0 0 18px rgba(61,220,151,.35)}
  .step-titles{flex:1;min-width:240px}
  .step-titles h3{margin:0;font-size:1.3rem;letter-spacing:-.2px;color:var(--text)}
  .step-titles .tag{font-size:.8rem;color:var(--accent);font-weight:700;text-transform:uppercase;letter-spacing:.05em}

  .step-desc{color:var(--muted);font-size:.96rem;line-height:1.65;margin:0 0 20px}
  .step-desc b{color:var(--text)}

  .callout{border-radius:12px;padding:16px 20px;margin:18px 0;font-size:.93rem;line-height:1.6}
  .callout.warn{background:rgba(255,107,107,.08);border:1px solid rgba(255,107,107,.35);color:#fca5a5}
  .callout.warn b{color:#ff6b6b}
  .callout.tip{background:rgba(0,246,246,.07);border:1px solid rgba(0,246,246,.3);color:#c4f4f4}
  .callout.tip b{color:var(--accent)}
  .callout.success{background:rgba(61,220,151,.08);border:1px solid rgba(61,220,151,.35);color:#c0f2dc}
  .callout.success b{color:var(--green)}

  .choice-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:20px;margin:22px 0}
  .choice-card{background:#0d1629;border:1px solid var(--line);border-radius:14px;padding:24px;
    display:flex;flex-direction:column;transition:border-color .18s,transform .18s}
  .choice-card:hover{border-color:var(--accent-dim);transform:translateY(-2px)}
  .choice-card.highlight{border-color:rgba(0,246,246,.4)}
  .choice-card h4{margin:0 0 10px;font-size:1.2rem;color:var(--text);letter-spacing:-.2px}
  .choice-card .subtag{display:inline-block;font-size:.78rem;color:var(--accent);font-weight:800;letter-spacing:.06em;text-transform:uppercase;margin-bottom:8px}
  .choice-card .subtag.gold{color:var(--gold)}
  .choice-card .subtag.green{color:var(--green)}
  .choice-card p{color:var(--muted);font-size:.93rem;line-height:1.6;margin:0 0 16px;flex:1}
  .choice-card p b{color:var(--text)}
  .choice-card .card-tip{background:rgba(255,255,255,.04);border-radius:8px;padding:10px 12px;font-size:.85rem;color:var(--muted);margin-top:auto;line-height:1.5}
  .choice-card .card-tip b{color:var(--text)}
  .choice-card .card-tip.warn{background:rgba(255,107,107,.08);border:1px solid rgba(255,107,107,.25);color:#fca5a5}
  .choice-card .card-tip.warn b{color:#ff6b6b}
  .choice-card .card-tip.success{background:rgba(61,220,151,.08);border:1px solid rgba(61,220,151,.25);color:#c0f2dc}
  .choice-card .card-tip.success b{color:var(--green)}
  .choice-card .card-tip.tip{background:rgba(0,246,246,.08);border:1px solid rgba(0,246,246,.25);color:#c4f4f4}
  .choice-card .card-tip.tip b{color:var(--accent)}

  .faq-list{list-style:none;padding:0;margin:0;display:grid;gap:14px}
  .faq-item{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px 22px}
  .faq-item b{display:block;color:var(--accent);font-size:1.02rem;margin-bottom:8px}
  .faq-item p{margin:0;color:var(--muted);font-size:.94rem;line-height:1.6}
  .faq-item p b{display:inline;color:var(--text)}
  .faq-item a{color:var(--accent);text-decoration:none}
  .faq-item a:hover{text-decoration:underline}

  .action-row{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0 0}
  @media(max-width:760px){
    .step-box{padding:20px}
    .guide-hero{padding:32px 0 20px}
    .step-badge{width:38px;height:38px;font-size:1.1rem}
  }
"""

T = {
    "vi": {
        "lang": "vi", "other": "en", "other_name": "English",
        "canon": f"{DOMAIN}/vi/guide/",
        "otherhome": f"{DOMAIN}/guide/",
        "title": "Hướng dẫn người mới: Cài đặt trọn gói Full ROM & RetroHub từ A-Z — RetroHub",
        "desc": "Hướng dẫn người mới cài máy TrimUI siêu tốc chỉ với 3 bước: Tải gói Full tích hợp sẵn -> Format thẻ nhớ exFAT -> Chép vào thẻ nhớ -> Done!",
        "keywords": "cài retrohub, hướng dẫn trimui, cài rom trimui brick, sd base package trimui, retrohub cho người mới, rom full trimui, crossmix",
        "og_desc": "Hướng dẫn siêu tốc cho người mới: Tải bản Full tích hợp -> Format thẻ nhớ exFAT -> Chép sang thẻ -> Done!",
        "badge": "HƯỚNG DẪN SIÊU TỐC CHO NGƯỜI MỚI (ALL-IN-ONE)",
        "h1": "Quy trình 3 bước cho người mới",
        "sub": "Đúng 3 thao tác đơn giản: Tải gói Full tích hợp → Format thẻ nhớ exFAT → Chép vào thẻ là XONG (Done). Đã có sẵn ROM gốc, full giả lập, Java J2ME và RetroHub v1.97 mới nhất!",
        "meta_time_k": "Thời gian thực hiện", "meta_time_v": "Khoảng 5 – 10 phút cực nhanh",
        "meta_sd_k": "Thẻ nhớ khuyến nghị", "meta_sd_v": "64GB – 256GB chính hãng (chuẩn exFAT)",
        "meta_os_k": "Thiết bị hỗ trợ", "meta_os_v": "TrimUI Brick, Brick Pro, Smart Pro",
        "meta_ota_k": "Cập nhật sau này", "meta_ota_v": "Tự động 100% qua Wi-Fi (Không cần tháo thẻ)",
        "cta_main": "Tải bản Full tích hợp (1.05 GB) ⤓",
        "cta_start": "Xem 3 bước cài đặt ↓",
        "cta_alone": "Cài lẻ vào thẻ cũ ↓",
    },
    "en": {
        "lang": "en", "other": "vi", "other_name": "Tiếng Việt",
        "canon": f"{DOMAIN}/guide/",
        "otherhome": f"{DOMAIN}/vi/guide/",
        "title": "Beginner Setup Guide: All-in-One Full ROM & RetroHub — RetroHub",
        "desc": "Ultra-simple 3-step setup guide for TrimUI handhelds: Download All-in-One package -> Format SD card to exFAT -> Copy to SD card -> Done!",
        "keywords": "install retrohub, trimui beginner guide, trimui brick setup, sd base package, full rom trimui, retrohub all in one",
        "og_desc": "Superfast 3-step guide: Download full all-in-one package -> Format SD card as exFAT -> Copy to card -> Done!",
        "badge": "STREAMLINED BEGINNER SETUP GUIDE (ALL-IN-ONE)",
        "h1": "3-Step Setup for Beginners",
        "sub": "Just 3 simple steps: Download All-in-One Package → Format SD as exFAT → Copy to SD Card → DONE! Pre-configured with stock ROM, full emulators, Java J2ME, and latest RetroHub v1.97.",
        "meta_time_k": "Estimated Time", "meta_time_v": "About 5 – 10 minutes",
        "meta_sd_k": "Recommended Card", "meta_sd_v": "64GB – 256GB genuine card (exFAT format)",
        "meta_os_k": "Supported Consoles", "meta_os_v": "TrimUI Brick, Brick Pro, Smart Pro",
        "meta_ota_k": "Future Updates", "meta_ota_v": "100% automated over Wi-Fi (No card removal)",
        "cta_main": "Download All-in-One (1.05 GB) ⤓",
        "cta_start": "Follow 3 Steps ↓",
        "cta_alone": "Existing SD Card ↓",
    }
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
<link rel="alternate" hreflang="en" href="{DOMAIN}/guide/">
<link rel="alternate" hreflang="vi" href="{DOMAIN}/vi/guide/">
<link rel="alternate" hreflang="x-default" href="{DOMAIN}/guide/">
<link rel="icon" href="/logo.png">
<link rel="apple-touch-icon" href="/logo.png">
<meta property="og:type" content="article">
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
<style>
{css}
{extracss}
</style>
</head>
<body>

<nav>
  <div class="navin">
    <a class="brand" href="{home_url}"><img src="/logo.png" alt=""><span>RetroHub</span></a>
    <div class="navlinks">{navlinks}</div>
    <a class="lang" href="{other_url}" hreflang="{other}" title="{other_name}">
      <img src="/files/assets/flag_{other}.png" alt=""><span>{other_name}</span></a>
  </div>
</nav>

<header class="guide-hero">
  <div class="wrap">
    <span class="badge-hero">{badge}</span>
    <h1>{h1}</h1>
    <p class="sub" style="max-width:820px;margin:0 auto 24px">{sub}</p>

    <div class="cta">
      <a class="btn" href="{SD_FULL_URL}">{cta_main}</a>
      <a class="btn alt" href="#quy-trinh">{cta_start}</a>
      <a class="btn ghost" href="#cai-le">{cta_alone}</a>
    </div>

    <div class="guide-meta">
      <div class="meta-card"><b>{meta_time_k}</b><span>{meta_time_v}</span></div>
      <div class="meta-card"><b>{meta_sd_k}</b><span>{meta_sd_v}</span></div>
      <div class="meta-card"><b>{meta_os_k}</b><span>{meta_os_v}</span></div>
      <div class="meta-card"><b>{meta_ota_k}</b><span>{meta_ota_v}</span></div>
    </div>

    <ul class="toc-nav">{toc}</ul>
  </div>
</header>

<main class="wrap" style="padding-bottom:72px">
{content}
</main>

<script>
(function(){
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  function showAll() {
    [].forEach.call(document.querySelectorAll(".rise"), function (el) { el.classList.add("seen"); });
  }
  if (location.hash || reduce || !("IntersectionObserver" in window)) {
    showAll();
  } else {
    var rev = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add("seen");
          rev.unobserve(e.target);
        }
      });
    }, { rootMargin: "0px 0px -10% 0px" });
    [].forEach.call(document.querySelectorAll(".rise"), function (el) { rev.observe(el); });
  }
  window.addEventListener("hashchange", showAll);
})();
</script>
</body>
</html>
"""


def render_content_vi():
    return f"""
  <!-- SECTION: QUY TRÌNH 3 BƯỚC SIÊU TỐC -->
  <section id="quy-trinh" class="rise">
    <h2>Quy trình 3 bước siêu tốc cho người mới</h2>
    <div class="step-box">
      <p class="step-desc" style="font-size:1.02rem;margin-bottom:20px">
        Bạn mới mua máy TrimUI hoặc có thẻ nhớ trắng tinh và không biết bắt đầu từ đâu? <b>Không cần tải lắt nhắt nhiều phần mềm riêng</b>, toàn bộ hệ điều hành, giả lập và RetroHub đã được gom thành <b>1 file ZIP duy nhất</b>:
      </p>
      <div class="choice-grid">
        <div class="choice-card highlight">
          <span class="subtag">BƯỚC 1</span>
          <h4>1. Tải bản Full All-in-One</h4>
          <p>Tải 1 gói ZIP hoàn chỉnh duy nhất (1.05 GB) chứa trọn bộ: ROM nền hệ máy, BIOS, core RetroArch, giả lập Java J2ME, Sega CD và ứng dụng <b>RetroHub v{VERSION}</b> mới nhất.</p>
          <div style="margin-bottom:14px">
            <a class="btn" style="display:block;padding:12px 16px;font-size:.92rem" href="{SD_FULL_URL}">
              Tải bản Full (1.05 GB) ⤓
            </a>
          </div>
          <div class="card-tip tip">
            <b>Đã tích hợp sẵn:</b> SD base tg4040, giả lập Java J2ME, 40.000 game catalog, tải trực tiếp từ GitHub Releases.
          </div>
        </div>

        <div class="choice-card highlight">
          <span class="subtag gold">BƯỚC 2</span>
          <h4>2. Format thẻ nhớ exFAT</h4>
          <p>Chuẩn bị thẻ nhớ MicroSD (64GB – 256GB). Cắm thẻ vào máy tính và định dạng sang chuẩn <b>exFAT</b>:
            <br>• <b>Windows:</b> Chuột phải ổ thẻ nhớ → Chọn <i>Format...</i> → File system: <b>exFAT</b> → Bấm <i>Start</i>.
            <br>• <b>macOS:</b> Mở <i>Disk Utility</i> → Chọn thẻ nhớ → Bấm <i>Erase</i> → Format: <b>ExFAT</b>.
          </p>
          <div class="card-tip warn">
            <b>Bắt buộc chọn exFAT:</b> Tuyệt đối không dùng FAT32 để tránh lỗi không nhận thẻ và treo logo TrimUI lúc khởi động.
          </div>
        </div>

        <div class="choice-card highlight">
          <span class="subtag green">BƯỚC 3</span>
          <h4>3. Chép vào thẻ nhớ & Done!</h4>
          <p>Dùng 7-Zip hoặc WinRAR giải nén file ZIP vừa tải ở Bước 1. Copy toàn bộ các thư mục bên trong (<code>Apps</code>, <code>Emus</code>, <code>RetroArch</code>, <code>Roms</code>, <code>System</code>,...) dán thẳng vào thư mục gốc của thẻ nhớ SD.</p>
          <div class="card-tip success">
            <b>Xong (Done!):</b> Cắm thẻ vào máy TrimUI, bật nguồn là sẵn sàng chơi ngay! Vào <b>Apps → RetroHub</b> để tải thêm game qua Wi-Fi.
          </div>
        </div>
      </div>

      <div class="callout success" style="margin-top:24px">
        <b>Đặc quyền tự động hoá:</b> Bạn chỉ cần làm qua máy tính đúng <b>một lần duy nhất</b> này. Từ nay về sau, khi có game mới hay tính năng mới, RetroHub tự động cập nhật online qua Wi-Fi ngay trên máy mà không bao giờ cần rút thẻ nhớ nữa!
      </div>
    </div>
  </section>

  <!-- OPTIONAL: EXISTING SD CARD -->
  <section id="cai-le" class="step-box rise" style="margin-top:36px">
    <div class="step-hdr">
      <div class="step-badge alt">+</div>
      <div class="step-titles">
        <span class="tag">TÙY CHỌN DÀNH CHO THẺ NHỚ CŨ</span>
        <h3>Đã có sẵn thẻ nhớ? Chỉ cài lẻ RetroHub</h3>
      </div>
    </div>

    <p class="step-desc">
      Nếu máy bạn đã có sẵn thẻ nhớ đang dùng ổn định và bạn <b>chỉ muốn cài thêm ứng dụng RetroHub</b> mà không muốn format hay cài lại từ đầu:
    </p>

    <div class="choice-grid">
      <div class="choice-card highlight">
        <span class="subtag">TRIMUI HỆ GỐC & CROSSMIX</span>
        <h4>Bản cho TrimUI (Stock OS)</h4>
        <p>Giải nén và chép thư mục <code>RetroHub</code> vào <code>/Apps/</code> trên thẻ nhớ. Mở Apps → RetroHub.</p>
        <a class="btn" href="{REL}/{VER_FULL}">Tải {VER_FULL} <small>95 MB · Kèm giả lập Java</small></a>
      </div>

      <div class="choice-card">
        <span class="subtag">HỆ ĐIỀU HÀNH NEXTUI</span>
        <h4>Bản cho NextUI (Tool Pak)</h4>
        <p>Giải nén và chép thư mục <code>Tools</code> vào thư mục gốc của thẻ nhớ. Mở Tools → RetroHub.</p>
        <a class="btn" href="{REL}/{VER_NEXTUI}">Tải {VER_NEXTUI} <small>192 MB · Chuẩn NextUI Pak</small></a>
      </div>
    </div>
  </section>

  <!-- FAQ -->
  <section id="faq" class="step-box rise" style="margin-top:36px">
    <div class="step-hdr">
      <div class="step-badge alt">?</div>
      <div class="step-titles">
        <span class="tag">GIẢI ĐÁP THẮC MẮC</span>
        <h3>Câu Hỏi Thường Gặp & Xử Lý Sự Cố</h3>
      </div>
    </div>

    <ul class="faq-list">
      <li class="faq-item">
        <b>Tôi cắm thẻ vào máy nhưng bị treo ở logo TrimUI lúc khởi động?</b>
        <p>Lỗi này 100% là do thẻ nhớ chưa được format chuẩn <b>exFAT</b> hoặc dùng thẻ nhớ kém chất lượng. Hãy format lại thẻ sang chuẩn exFAT (như Bước 2) và chép lại dữ liệu.</p>
      </li>
      <li class="faq-item">
        <b>Bản Full này đã có sẵn game chưa hay phải tự tải?</b>
        <p>Gói này đã cài đặt sẵn hệ thống, BIOS, core giả lập và ứng dụng RetroHub. Bạn chỉ cần mở RetroHub lên (khi có Wi-Fi) để tha hồ chọn và tải trực tiếp bất kỳ tựa game nào trong kho gần 40.000 game, hoặc dùng SFTP để chép ROM từ máy tính sang.</p>
      </li>
      <li class="faq-item">
        <b>Muốn chép thêm ROM game có sẵn từ máy tính thì bỏ vào đâu?</b>
        <p>Bỏ vào thư mục <code>/Roms/[TÊN_HỆ_MÁY]/</code> trên thẻ nhớ (ví dụ: game GBA bỏ vào <code>/Roms/GBA/</code>, PS1 bỏ vào <code>/Roms/PS/</code>). Sau đó trên màn hình máy cầm tay, bấm nút <b>Menu</b> và chọn <b>Refresh Roms</b>.</p>
      </li>
      <li class="faq-item">
        <b>Sau này có bản cập nhật mới thì làm thế nào?</b>
        <p><b>Hoàn toàn tự động!</b> Chỉ cần kết nối Wi-Fi trên máy TrimUI và mở RetroHub lên, ứng dụng sẽ báo cập nhật và tự động nâng cấp trực tiếp ngay trên máy trong vài giây.</p>
      </li>
    </ul>

    <div class="callout tip" style="margin-top:24px">
      <b>Cần hỗ trợ thêm hoặc giao lưu cùng cộng đồng?</b><br>
      Tham gia nhóm Telegram cộng đồng RetroHub để được hỗ trợ giải đáp trực tiếp:
      <div class="action-row">
        <a class="btn" href="https://t.me/retrohubtool" target="_blank" rel="noopener noreferrer">Vào nhóm Telegram @retrohubtool</a>
        <a class="btn ghost" href="https://t.me/xuanhoa493" target="_blank" rel="noopener noreferrer">Nhắn tin tác giả @xuanhoa493</a>
      </div>
    </div>
  </section>
"""


def render_content_en():
    return f"""
  <!-- SECTION: 3-STEP SETUP -->
  <section id="quy-trinh" class="rise">
    <h2>Superfast 3-Step Setup for Beginners</h2>
    <div class="step-box">
      <p class="step-desc" style="font-size:1.02rem;margin-bottom:20px">
        Just got your TrimUI handheld or starting with a blank SD card? <b>No need to download multiple separate packages</b>. The complete system base, verified emulators, and RetroHub are bundled into <b>one single ZIP</b>:
      </p>
      <div class="choice-grid">
        <div class="choice-card highlight">
          <span class="subtag">STEP 1</span>
          <h4>1. Download All-in-One Package</h4>
          <p>Download a single comprehensive ZIP (1.05 GB) containing: Stock OS base, full BIOS, RetroArch cores, Java J2ME, Sega CD, and latest <b>RetroHub v{VERSION}</b>.</p>
          <div style="margin-bottom:14px">
            <a class="btn" style="display:block;padding:12px 16px;font-size:.92rem" href="{SD_FULL_URL}">
              Download All-in-One (1.05 GB) ⤓
            </a>
          </div>
          <div class="card-tip tip">
            <b>Pre-configured:</b> tg4040 SD base, Java J2ME runtime, 40,000 game catalog, direct GitHub Release download.
          </div>
        </div>

        <div class="choice-card highlight">
          <span class="subtag gold">STEP 2</span>
          <h4>2. Format SD Card as exFAT</h4>
          <p>Prepare a genuine MicroSD card (64GB – 256GB). Insert into your PC and format to <b>exFAT</b>:
            <br>• <b>Windows:</b> Right-click SD drive → <i>Format...</i> → File system: <b>exFAT</b> → Click <i>Start</i>.
            <br>• <b>macOS:</b> Open <i>Disk Utility</i> → Select SD → <i>Erase</i> → Format: <b>ExFAT</b>.
          </p>
          <div class="card-tip warn">
            <b>Mandatory exFAT:</b> Never use FAT32 to avoid file size limits and TrimUI logo boot freeze.
          </div>
        </div>

        <div class="choice-card highlight">
          <span class="subtag green">STEP 3</span>
          <h4>3. Copy to SD Card & Done!</h4>
          <p>Extract the downloaded ZIP using 7-Zip or WinRAR. Copy all internal folders (<code>Apps</code>, <code>Emus</code>, <code>RetroArch</code>, <code>Roms</code>, <code>System</code>,...) directly to the root of your SD card.</p>
          <div class="card-tip success">
            <b>Done & Ready:</b> Insert SD card into TrimUI, power on, and play! Open <b>Apps → RetroHub</b> to fetch games over Wi-Fi.
          </div>
        </div>
      </div>

      <div class="callout success" style="margin-top:24px">
        <b>Wireless Automation:</b> You only need a computer <b>once</b>. Future updates and new game downloads are handled 100% wirelessly over Wi-Fi right on the console!
      </div>
    </div>
  </section>

  <!-- OPTIONAL: EXISTING SD CARD -->
  <section id="cai-le" class="step-box rise" style="margin-top:36px">
    <div class="step-hdr">
      <div class="step-badge alt">+</div>
      <div class="step-titles">
        <span class="tag">FOR EXISTING SD CARDS</span>
        <h3>Already Have An SD Card? Install RetroHub Only</h3>
      </div>
    </div>

    <p class="step-desc">
      If you already have a working SD card with games and only want to add RetroHub without re-formatting:
    </p>

    <div class="choice-grid">
      <div class="choice-card highlight">
        <span class="subtag">TRIMUI STOCK OS & CROSSMIX</span>
        <h4>TrimUI (Stock OS)</h4>
        <p>Extract and copy the <code>RetroHub</code> folder into <code>/Apps/</code> on your SD card. Open Apps → RetroHub.</p>
        <a class="btn" href="{REL}/{VER_FULL}">Download {VER_FULL} <small>95 MB · Java emulator included</small></a>
      </div>

      <div class="choice-card">
        <span class="subtag">NEXTUI FIRMWARE</span>
        <h4>NextUI (Tool Pak)</h4>
        <p>Extract and copy the <code>Tools</code> folder to your SD card root. Open Tools → RetroHub.</p>
        <a class="btn" href="{REL}/{VER_NEXTUI}">Download {VER_NEXTUI} <small>192 MB · NextUI Pak</small></a>
      </div>
    </div>
  </section>

  <!-- FAQ -->
  <section id="faq" class="step-box rise" style="margin-top:36px">
    <div class="step-hdr">
      <div class="step-badge alt">?</div>
      <div class="step-titles">
        <span class="tag">FREQUENTLY ASKED QUESTIONS</span>
        <h3>Troubleshooting & Tips</h3>
      </div>
    </div>

    <ul class="faq-list">
      <li class="faq-item">
        <b>My device is stuck at the TrimUI logo on boot?</b>
        <p>This is almost always caused by formatting as <b>FAT32</b> or faulty partitions. Re-format your card as <b>exFAT</b> (Step 2) and copy the files again.</p>
      </li>
      <li class="faq-item">
        <b>Does this Full package include games already?</b>
        <p>It comes with the complete system base, BIOS, emulators, and RetroHub. Connect to Wi-Fi and open RetroHub to download from the 40,000 game library directly on device, or transfer ROMs from PC via SFTP.</p>
      </li>
      <li class="faq-item">
        <b>Where do I copy ROMs from my PC?</b>
        <p>Place them into <code>/Roms/[CONSOLE]/</code> on your SD card (e.g. GBA games into <code>/Roms/GBA/</code>). On your TrimUI home screen, press <b>Menu</b> and select <b>Refresh Roms</b>.</p>
      </li>
      <li class="faq-item">
        <b>How do updates work in the future?</b>
        <p><b>100% automated!</b> Connect your console to Wi-Fi and open RetroHub. It automatically detects and installs updates on-device in seconds.</p>
      </li>
    </ul>

    <div class="callout tip" style="margin-top:24px">
      <b>Need help or want to join the community?</b><br>
      Join our Telegram group for friendly support from fellow players:
      <div class="action-row">
        <a class="btn" href="https://t.me/retrohubtool" target="_blank" rel="noopener noreferrer">Join Telegram @retrohubtool</a>
        <a class="btn ghost" href="https://t.me/xuanhoa493" target="_blank" rel="noopener noreferrer">Message Author @xuanhoa493</a>
      </div>
    </div>
  </section>
"""


def render(lang):
    t = T[lang]
    canon = t["canon"]
    home_url = "/" if lang == "en" else "/vi/"
    other_url = t["otherhome"]

    idx = 1 if lang == "en" else 2
    toc = "".join(f'<li><a href="#{sec[0]}">{sec[idx]}</a></li>' for sec in SECTIONS)

    ld = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": t["title"],
        "description": t["desc"],
        "inLanguage": lang,
        "url": canon,
        "author": {
            "@type": "Person",
            "name": "Nguyễn Xuân Hòa",
            "url": "https://xuanhoa493.com"
        },
        "isPartOf": {
            "@type": "WebSite",
            "name": "RetroHub",
            "url": DOMAIN
        }
    }

    content = render_content_vi() if lang == "vi" else render_content_en()
    navlinks = navlinks_for(lang, "guide")

    fill = {
        "lang": lang,
        "title": t["title"],
        "desc": t["desc"],
        "keywords": t["keywords"],
        "canon": canon,
        "DOMAIN": DOMAIN,
        "oglocale": "en_US" if lang == "en" else "vi_VN",
        "og_desc": t["og_desc"],
        "ldjson": json.dumps(ld, ensure_ascii=False, indent=2),
        "css": CSS,
        "extracss": EXTRA_CSS,
        "home_url": home_url,
        "other_url": other_url,
        "other": t["other"],
        "other_name": t["other_name"],
        "navlinks": navlinks,
        "badge": t["badge"],
        "h1": t["h1"],
        "sub": t["sub"],
        "meta_time_k": t["meta_time_k"],
        "meta_time_v": t["meta_time_v"],
        "meta_sd_k": t["meta_sd_k"],
        "meta_sd_v": t["meta_sd_v"],
        "meta_os_k": t["meta_os_k"],
        "meta_os_v": t["meta_os_v"],
        "meta_ota_k": t["meta_ota_k"],
        "meta_ota_v": t["meta_ota_v"],
        "cta_main": t["cta_main"],
        "cta_start": t["cta_start"],
        "cta_alone": t["cta_alone"],
        "SD_FULL_URL": SD_FULL_URL,
        "VER_SD_FULL": VER_SD_FULL,
        "toc": toc,
        "content": content,
        "REL": REL,
        "VER_FULL": VER_FULL,
        "VER_NEXTUI": VER_NEXTUI,
        "VERSION": VERSION,
    }

    out = PAGE
    for k, v in fill.items():
        out = out.replace(f"{{{k}}}", str(v))

    left = re.findall(r"\{([a-zA-Z_]+)\}", out)
    if left:
        raise SystemExit(f"Missing placeholder replacement: {sorted(set(left))}")

    return out


def main():
    for lang in ("en", "vi"):
        path = os.path.join(ROOT, "guide/index.html" if lang == "en"
                            else "vi/guide/index.html")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(render(lang))
        print("  %-22s %6d byte" % (os.path.relpath(path, ROOT), os.path.getsize(path)))


if __name__ == "__main__":
    main()
