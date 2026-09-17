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
    VER_FULL, VER_NEXTUI, SD_FULL_URL, REL
)

SECTIONS = [
    ("quy-trinh", "7 Steps (Brick Pro)", "7 Bước (Brick Pro)"),
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

  .step-grid-7{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin:20px 0}
  .step-card-clean{background:#0d1629;border:1px solid var(--line);border-radius:12px;padding:20px;
    display:flex;flex-direction:column;position:relative;transition:border-color .18s,transform .18s}
  .step-card-clean:hover{border-color:var(--accent-dim);transform:translateY(-2px)}
  .step-card-clean.highlight{border-color:rgba(0,246,246,.4)}
  .step-card-clean .step-num{display:inline-flex;align-items:center;justify-content:center;
    width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,#0a8f96,#00f6f6);
    color:#04121b;font-weight:800;font-size:.95rem;margin-bottom:12px}
  .step-card-clean .step-num.gold{background:linear-gradient(135deg,#d4a017,#ffcf3c)}
  .step-card-clean .step-num.green{background:linear-gradient(135deg,#1f9d68,#3ddc97)}
  .step-card-clean h4{margin:0 0 8px;font-size:1.1rem;color:var(--text);letter-spacing:-.2px}
  .step-card-clean p{color:var(--muted);font-size:.9rem;line-height:1.55;margin:0 0 12px;flex:1}
  .step-card-clean p b{color:var(--text)}
  .step-card-clean .step-act{margin-top:auto}

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
        "title": "Hướng dẫn người mới: Cài đặt Full ROM & RetroHub (7 Bước) — RetroHub",
        "desc": "Hướng dẫn người mới cài máy TrimUI từ A-Z với 7 bước đơn giản: Tải ROM Stock Full, format thẻ exFAT, cài RetroHub và trải nghiệm!",
        "keywords": "cài retrohub, hướng dẫn trimui, cài rom trimui brick, sd base package trimui, retrohub cho người mới, rom full trimui, crossmix",
        "og_desc": "Hướng dẫn 7 bước cho người mới: Tải ROM Stock Full -> Format thẻ exFAT -> Cài RetroHub -> Xong!",
        "badge": "HƯỚNG DẪN CÀI ĐẶT CHO NGƯỜI MỚI (7 BƯỚC)",
        "h1": "7 Bước cài đặt trọn gói từ A-Z",
        "sub": f"Quy trình 7 bước chuẩn: Tải ROM gốc DTH → Format thẻ exFAT → Cài RetroHub v{VERSION} mới nhất. Gọn nhẹ, dễ làm và 100% tự động cập nhật về sau!",
        "meta_time_k": "Thời gian thực hiện", "meta_time_v": "Khoảng 5 – 10 phút",
        "meta_sd_k": "Thẻ nhớ khuyến nghị", "meta_sd_v": "64GB – 256GB (Chuẩn exFAT)",
        "meta_os_k": "Nguồn ROM Stock", "meta_os_v": "DTH-RetroHandheld (Brick Pro)",
        "meta_ota_k": "Cập nhật sau này", "meta_ota_v": "Tự động qua Wi-Fi",
        "cta_main": "Tải ROMs Stock Full (DTH) ↗",
        "cta_start": "Xem 7 bước cài đặt ↓",
        "cta_alone": "Cài lẻ vào thẻ cũ ↓",
    },
    "en": {
        "lang": "en", "other": "vi", "other_name": "Tiếng Việt",
        "canon": f"{DOMAIN}/guide/",
        "otherhome": f"{DOMAIN}/vi/guide/",
        "title": "Beginner Setup Guide: Full ROM & RetroHub in 7 Steps — RetroHub",
        "desc": "Step-by-step 7-step beginner guide for TrimUI handhelds: Download Stock Full ROMs, format SD to exFAT, install RetroHub and play!",
        "keywords": "install retrohub, trimui beginner guide, trimui brick setup, sd base package, full rom trimui, retrohub setup",
        "og_desc": "7-Step beginner guide: Download Stock ROMs -> Format SD exFAT -> Install RetroHub -> Done!",
        "badge": "BEGINNER SETUP GUIDE (7 STEPS)",
        "h1": "7-Step Setup Guide from A to Z",
        "sub": f"Streamlined 7-step guide: Download official DTH Stock ROMs → Format SD as exFAT → Install latest RetroHub v{VERSION}. Fast, simple, and self-updating over Wi-Fi!",
        "meta_time_k": "Estimated Time", "meta_time_v": "About 5 – 10 minutes",
        "meta_sd_k": "Recommended Card", "meta_sd_v": "64GB – 256GB (exFAT format)",
        "meta_os_k": "Stock ROM Source", "meta_os_v": "DTH-RetroHandheld (Brick Pro)",
        "meta_ota_k": "Future Updates", "meta_ota_v": "100% automated over Wi-Fi",
        "cta_main": "Download Stock Full ROMs (DTH) ↗",
        "cta_start": "Follow 7 Steps ↓",
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
  <!-- SECTION: QUY TRÌNH 7 BƯỚC -->
  <section id="quy-trinh" class="rise">
    <h2>Quy trình 7 bước cho máy TrimUI Brick Pro</h2>
    <div class="step-box">
      <p class="step-desc" style="font-size:1.02rem;margin-bottom:20px">
        Bạn mới mua máy TrimUI Brick Pro hoặc có thẻ nhớ trắng tinh? Thực hiện theo đúng <b>7 bước ngắn gọn</b> sau để cài đặt toàn bộ hệ thống giả lập và RetroHub:
      </p>

      <div class="step-grid-7">
        <div class="step-card-clean highlight">
          <span class="step-num">1</span>
          <h4>1. Tải ROMs Stock Full</h4>
          <p>Tải gói giả lập & ROM gốc từ trang release chính thức của DTH-RetroHandheld.</p>
          <div class="step-act">
            <a class="btn" style="display:block;padding:10px 14px;font-size:.88rem" href="{SD_FULL_URL}" target="_blank" rel="noopener">
              Mở link tải DTH Releases ↗
            </a>
          </div>
        </div>

        <div class="step-card-clean">
          <span class="step-num gold">2</span>
          <h4>2. Format thẻ về exFAT</h4>
          <p>Cắm thẻ nhớ MicroSD (64GB - 256GB) vào máy tính và định dạng sang chuẩn <b>exFAT</b> (bắt buộc exFAT để tránh lỗi không nhận thẻ).</p>
        </div>

        <div class="step-card-clean">
          <span class="step-num">3</span>
          <h4>3. Giải nén ROM ra thẻ nhớ</h4>
          <p>Dùng 7-Zip hoặc WinRAR giải nén gói vừa tải, chép toàn bộ các thư mục (<code>Apps</code>, <code>Emus</code>, <code>Roms</code>, <code>System</code>...) vào thư mục gốc của thẻ nhớ.</p>
        </div>

        <div class="step-card-clean">
          <span class="step-num gold">4</span>
          <h4>4. Khởi động lại máy để cài ROM</h4>
          <p>Cắm thẻ nhớ vào máy TrimUI và bật nguồn lên một lần để hệ thống nạp và nhận diện toàn bộ trình giả lập.</p>
        </div>

        <div class="step-card-clean highlight">
          <span class="step-num green">5</span>
          <h4>5. Tải RetroHub mới nhất</h4>
          <p>Tải bản cài đặt RetroHub v{VERSION} mới nhất dành cho hệ điều hành gốc:</p>
          <div class="step-act">
            <a class="btn" style="display:block;padding:10px 14px;font-size:.88rem" href="{REL}/{VER_FULL}">
              Tải RetroHub (Stock) v{VERSION} ⤓
            </a>
          </div>
        </div>

        <div class="step-card-clean">
          <span class="step-num">6</span>
          <h4>6. Copy RetroHub vào Apps</h4>
          <p>Giải nén file tải ở bước 5, copy thư mục <code>RetroHub</code> dán vào thư mục <code>/Apps/</code> trên thẻ nhớ.</p>
        </div>

        <div class="step-card-clean highlight">
          <span class="step-num green">7</span>
          <h4>7. Khởi động lại máy và mở app</h4>
          <p>Bật máy cầm tay, truy cập vào <b>Apps → RetroHub</b> để khám phá kho 40.000 game và tận hưởng tự động cập nhật qua Wi-Fi!</p>
        </div>
      </div>

      <div class="callout success" style="margin-top:20px">
        <b>Đặc quyền tự động hoá:</b> Bạn chỉ cần thực hiện 7 bước qua máy tính <b>đúng một lần duy nhất</b>. Về sau ứng dụng tự động kiểm tra và nâng cấp trực tiếp qua Wi-Fi.
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
      Nếu thẻ nhớ đã có sẵn game và bạn chỉ muốn cài thêm RetroHub:
    </p>

    <div class="choice-grid">
      <div class="choice-card highlight">
        <span class="subtag">TRIMUI HỆ GỐC & CROSSMIX</span>
        <h4>Bản cho TrimUI (Stock OS)</h4>
        <p>Giải nén và chép thư mục <code>RetroHub</code> vào <code>/Apps/</code> trên thẻ nhớ. Mở Apps → RetroHub.</p>
        <a class="btn" href="{REL}/{VER_FULL}">Tải {VER_FULL} <small>8.3 MB · Kèm giả lập Java</small></a>
      </div>

      <div class="choice-card">
        <span class="subtag">HỆ ĐIỀU HÀNH NEXTUI</span>
        <h4>Bản cho NextUI (Tool Pak)</h4>
        <p>Giải nén và chép thư mục <code>Tools</code> vào thư mục gốc của thẻ nhớ. Mở Tools → RetroHub.</p>
        <a class="btn" href="{REL}/{VER_NEXTUI}">Tải {VER_NEXTUI} <small>8.3 MB · Chuẩn NextUI Pak</small></a>
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
        <p>Lỗi này do thẻ nhớ chưa được format chuẩn <b>exFAT</b>. Hãy format lại thẻ sang chuẩn exFAT (như Bước 2) và chép lại dữ liệu.</p>
      </li>
      <li class="faq-item">
        <b>Muốn chép thêm ROM game có sẵn từ máy tính thì bỏ vào đâu?</b>
        <p>Bỏ vào thư mục <code>/Roms/[TÊN_HỆ_MÁY]/</code> trên thẻ nhớ (ví dụ: game GBA bỏ vào <code>/Roms/GBA/</code>, PS1 bỏ vào <code>/Roms/PS/</code>). Sau đó trên máy bấm <b>Menu → Refresh Roms</b>.</p>
      </li>
      <li class="faq-item">
        <b>Sau này có bản cập nhật mới thì làm thế nào?</b>
        <p><b>Hoàn toàn tự động!</b> Chỉ cần kết nối Wi-Fi trên máy và mở RetroHub lên, ứng dụng sẽ báo cập nhật và tự động nâng cấp trực tiếp ngay trên máy trong vài giây.</p>
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
  <!-- SECTION: 7-STEP SETUP -->
  <section id="quy-trinh" class="rise">
    <h2>7-Step Setup Guide for TrimUI Brick Pro</h2>
    <div class="step-box">
      <p class="step-desc" style="font-size:1.02rem;margin-bottom:20px">
        Just got your TrimUI Brick Pro handheld or starting with a fresh SD card? Follow these <b>7 straightforward steps</b> to install full emulators and RetroHub:
      </p>

      <div class="step-grid-7">
        <div class="step-card-clean highlight">
          <span class="step-num">1</span>
          <h4>1. Download Stock Full ROMs</h4>
          <p>Get the full emulator base from the official DTH-RetroHandheld release page.</p>
          <div class="step-act">
            <a class="btn" style="display:block;padding:10px 14px;font-size:.88rem" href="{SD_FULL_URL}" target="_blank" rel="noopener">
              Open DTH Releases ↗
            </a>
          </div>
        </div>

        <div class="step-card-clean">
          <span class="step-num gold">2</span>
          <h4>2. Format SD Card as exFAT</h4>
          <p>Insert your MicroSD card (64GB - 256GB) into PC and format to <b>exFAT</b> (mandatory to avoid card recognition errors).</p>
        </div>

        <div class="step-card-clean">
          <span class="step-num">3</span>
          <h4>3. Extract ROMs to SD Card</h4>
          <p>Extract the downloaded archive using 7-Zip or WinRAR. Copy all internal folders (<code>Apps</code>, <code>Emus</code>, <code>Roms</code>, <code>System</code>...) directly to SD card root.</p>
        </div>

        <div class="step-card-clean">
          <span class="step-num gold">4</span>
          <h4>4. Reboot Console to Load ROMs</h4>
          <p>Insert the SD card into TrimUI and power on once so the OS registers and initializes all emulators.</p>
        </div>

        <div class="step-card-clean highlight">
          <span class="step-num green">5</span>
          <h4>5. Download Latest RetroHub</h4>
          <p>Download the latest RetroHub v{VERSION} installation package for Stock OS:</p>
          <div class="step-act">
            <a class="btn" style="display:block;padding:10px 14px;font-size:.88rem" href="{REL}/{VER_FULL}">
              Download RetroHub (Stock) v{VERSION} ⤓
            </a>
          </div>
        </div>

        <div class="step-card-clean">
          <span class="step-num">6</span>
          <h4>6. Copy RetroHub to Apps</h4>
          <p>Extract the file from Step 5, copy the <code>RetroHub</code> folder into <code>/Apps/</code> on your SD card.</p>
        </div>

        <div class="step-card-clean highlight">
          <span class="step-num green">7</span>
          <h4>7. Reboot & Open App</h4>
          <p>Turn on your console, navigate to <b>Apps → RetroHub</b> to access 40,000+ games and enjoy Wi-Fi auto-updates!</p>
        </div>
      </div>

      <div class="callout success" style="margin-top:20px">
        <b>Wireless Automation:</b> You only perform these 7 steps via computer <b>once</b>. All future updates are handled wirelessly over Wi-Fi right on the console!
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
      If you already have a working SD card with games and only want to add RetroHub:
    </p>

    <div class="choice-grid">
      <div class="choice-card highlight">
        <span class="subtag">TRIMUI STOCK OS & CROSSMIX</span>
        <h4>TrimUI (Stock OS)</h4>
        <p>Extract and copy the <code>RetroHub</code> folder into <code>/Apps/</code> on your SD card. Open Apps → RetroHub.</p>
        <a class="btn" href="{REL}/{VER_FULL}">Download {VER_FULL} <small>8.3 MB · Java emulator included</small></a>
      </div>

      <div class="choice-card">
        <span class="subtag">NEXTUI FIRMWARE</span>
        <h4>NextUI (Tool Pak)</h4>
        <p>Extract and copy the <code>Tools</code> folder to your SD card root. Open Tools → RetroHub.</p>
        <a class="btn" href="{REL}/{VER_NEXTUI}">Download {VER_NEXTUI} <small>8.3 MB · NextUI Pak</small></a>
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
        <p>This is almost always caused by formatting as <b>FAT32</b>. Re-format your card as <b>exFAT</b> (Step 2) and copy the files again.</p>
      </li>
      <li class="faq-item">
        <b>Where do I copy ROMs from my PC?</b>
        <p>Place them into <code>/Roms/[CONSOLE]/</code> on your SD card (e.g. GBA games into <code>/Roms/GBA/</code>). On your TrimUI home screen, press <b>Menu → Refresh Roms</b>.</p>
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
