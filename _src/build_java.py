#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render the Java J2ME guide in both languages from one table of content.

    python3 _src/build_java.py

Writes java/index.html (English) and vi/java/index.html. Same shape as
build.py and the same CSS, imported rather than copied so the two pages cannot
drift apart visually.

Everything here was checked against the shipped emulator rather than taken from
its README: the pad layouts come from the package's own guide, the per-game
phone modes from game.conf files read off a Brick Pro, and the scaling numbers
are worked out for that device's 1024x768 panel.
"""

import json
import os
import re

from build import CSS, DOMAIN, navlinks_for

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Sections, in page order: (anchor id, English nav label, Vietnamese nav label).
SECTIONS = [
    ("cai-dat", "Install", "Cài giả lập"),
    ("thu-muc", "Where games go", "Bỏ game vào đâu"),
    ("che-do-may", "Phone modes", "Chế độ máy"),
    ("nut-bam", "Button layouts", "Bố trí nút"),
    ("hinh-anh", "Display", "Hình ảnh"),
    ("toan-man-hinh", "Full screen", "Toàn màn hình"),
    ("luu-game", "Saves", "Save game"),
    ("su-co", "Troubleshooting", "Xử lý sự cố"),
]

# Physical pad layouts H / K / X, from the emulator package's own guide.
PAD_ROWS = [
    (("A", "Right softkey", "D-pad right", "OK"),
     ("A", "Phím chọn phải", "D-pad phải", "OK")),
    (("B", "Key 0", "D-pad down", "Right softkey"),
     ("B", "Số 0", "D-pad xuống", "Phím chọn phải")),
    (("X", "OK", "D-pad up", "Left softkey"),
     ("X", "OK", "D-pad lên", "Phím chọn trái")),
    (("Y", "Left softkey", "D-pad left", "Key 0"),
     ("Y", "Phím chọn trái", "D-pad trái", "Số 0")),
    (("D-pad up", "D-pad up", "Key 1", "D-pad up"),
     ("D-pad lên", "D-pad lên", "Số 1", "D-pad lên")),
    (("D-pad down", "D-pad down", "Key 3", "D-pad down"),
     ("D-pad xuống", "D-pad xuống", "Số 3", "D-pad xuống")),
    (("D-pad left", "D-pad left", "Key 7", "D-pad left"),
     ("D-pad trái", "D-pad trái", "Số 7", "D-pad trái")),
    (("D-pad right", "D-pad right", "Key 9", "D-pad right"),
     ("D-pad phải", "D-pad phải", "Số 9", "D-pad phải")),
    (("L1", "Key 1", "*", "Key 1"), ("L1", "Số 1", "*", "Số 1")),
    (("L2", "Key 3", "#", "Key 3"), ("L2", "Số 3", "#", "Số 3")),
    (("R1", "Key 9", "Right softkey", "Key 9"),
     ("R1", "Số 9", "Phím chọn phải", "Số 9")),
    (("R2", "Key 7", "OK", "Key 7"), ("R2", "Số 7", "OK", "Số 7")),
    (("L3", "*", "Key 0", "*"), ("L3", "*", "Số 0", "*")),
    (("R3", "#", "Left softkey", "#"), ("R3", "#", "Phím chọn trái", "#")),
    (("Left stick", "D-pad", "D-pad", "D-pad"),
     ("Cần trái", "D-pad", "D-pad", "D-pad")),
    (("Right stick", "2 / 4 / 6 / 8", "2 / 4 / 6 / 8", "2 / 4 / 6 / 8"),
     ("Cần phải", "2 / 4 / 6 / 8", "2 / 4 / 6 / 8", "2 / 4 / 6 / 8")),
    (("SELECT", "Key 5", "Key 5", "Key 5"), ("SELECT", "Số 5", "Số 5", "Số 5")),
    (("START", "—", "—", "—"), ("START", "—", "—", "—")),
]

# The five phone modes FreeJ2ME can pretend to be.
PHONE_ROWS = [
    (("P", "Plain keypad. The D-pad sends the digits 2/4/6/8 and OK sends 5."),
     ("P", "Bàn phím số phổ thông. D-pad gửi ra số 2/4/6/8, OK gửi số 5.")),
    (("N", "Nokia. The D-pad and OK arrive as GameAction — what most games expect."),
     ("N", "Nokia. D-pad và OK tới game dưới dạng GameAction — thứ đa số game chờ.")),
    (("E", "Sony Ericsson. A handful of titles need this and nothing else works."),
     ("E", "Sony Ericsson. Vài tựa chỉ chạy đúng ở chế độ này.")),
    (("S", "Siemens."), ("S", "Siemens.")),
    (("M", "Motorola."), ("M", "Motorola.")),
]

# renderer.conf keys. Three are read by the native side, three by the Java side.
CONF_ROWS = [
    (("render_mode", "pixel, smooth, hq",
      "Filter used when SDL scales the finished frame."),
     ("render_mode", "pixel, smooth, hq",
      "Bộ lọc khi SDL phóng khung hình cuối.")),
    (("integer_scaling", "true, false",
      "Round the scale factor down to a whole number while magnifying."),
     ("integer_scaling", "true, false",
      "Làm tròn hệ số phóng xuống số nguyên khi đang phóng to.")),
    (("keep_aspect", "true, false",
      "Keep the game's proportions. false stretches to fill the panel."),
     ("keep_aspect", "true, false",
      "Giữ đúng tỉ lệ hình. Để false là kéo giãn cho đầy màn.")),
    (("text_aa", "true, false", "Anti-alias Java/AWT text."),
     ("text_aa", "true, false", "Khử răng cưa chữ Java/AWT.")),
    (("shape_aa", "true, false", "Anti-alias Java/AWT lines and shapes."),
     ("shape_aa", "true, false", "Khử răng cưa đường và vùng vector Java/AWT.")),
    (("m3g_filter", "auto, nearest, linear",
      "Texture filter for 3D (M3G) games."),
     ("m3g_filter", "auto, nearest, linear",
      "Bộ lọc texture cho game 3D (M3G).")),
]

# Getting a 240x320 game onto a 1024x768 panel. Numbers, not adjectives.
FIT_ROWS = [
    (("SMOOTH or HQ", "576 × 768", "Correct",
      "Scale 2.4×, the largest that fits. Fills the full height, 224 px of border each side."),
     ("SMOOTH hoặc HQ", "576 × 768", "Đúng",
      "Phóng 2,4× — mức lớn nhất lọt màn. Đầy trọn chiều cao, mỗi bên còn 224 px viền.")),
    (("PIXEL", "480 × 640", "Correct",
      "Rounds 2.4 down to 2×, so the picture is smaller and there is border on all four sides."),
     ("PIXEL", "480 × 640", "Đúng",
      "Làm tròn 2,4 xuống 2×, nên hình nhỏ hơn và viền cả bốn phía.")),
    (("keep_aspect=false", "1024 × 768", "Stretched 1.78×",
      "Truly fills the panel. Width is magnified 4.27× against 2.4× for height, so everything looks fat."),
     ("keep_aspect=false", "1024 × 768", "Bè ngang 1,78 lần",
      "Lấp kín màn thật. Ngang phóng 4,27× trong khi dọc chỉ 2,4×, nên hình bè hẳn ra.")),
    (("Rotate the screen", "1024 × 768", "Correct",
      "START + B. Rotated the game is 320×240 — exactly 4:3, so it lands on the panel at 3.2× with no border at all. You hold the device sideways."),
     ("Xoay màn hình", "1024 × 768", "Đúng",
      "START + B. Xoay xong game thành 320×240 — đúng 4:3, khít màn ở 3,2×, không một pixel viền. Đổi lại phải cầm máy nằm ngang.")),
    (("Move to the 320240 folder", "1024 × 768", "Correct",
      "The game is handed a 320×240 landscape canvas, which also fits at 3.2×. Games that adapt to the canvas look best this way; games with a fixed portrait layout break."),
     ("Chuyển sang thư mục 320240", "1024 × 768", "Đúng",
      "Game được cấp khung 320×240 nằm ngang, cũng khít ở 3,2×. Game nào tự co giãn theo khung thì đẹp hẳn; game vẽ cứng theo khổ dọc thì vỡ bố cục.")),
]

SHORTCUTS = [
    (("START + SELECT", "Cycle P → N → E → S → M → H → K → X"),
     ("START + SELECT", "Chạy vòng P → N → E → S → M → H → K → X")),
    (("SELECT on its own", "Toggle display mode (Linear / Nearest)"),
     ("SELECT bấm riêng", "Đổi chế độ hiển thị (Linear / Nearest)")),
    (("MENU + D-pad Left", "Toggle diagonal D-pad to keys 1, 3, 7, 9"),
     ("MENU + D-pad Trái", "Chuyển các hướng chéo D-pad thành các phím 1, 3, 7, 9")),
    (("On-screen text input", "*: Delete, #: Add, 2/4: Letters a-z, 1/3: Digits 0-9, 7/9: Symbols"),
     ("Bàn phím ảo nhập text", "*: Xóa ký tự, #: Thêm, 2/4: Chọn chữ a-z, 1/3: Chọn số 0-9, 7/9: Ký tự đặc biệt")),
    (("START + R3", "Cycle PIXEL → SMOOTH → HQ"),
     ("START + R3", "Chạy vòng PIXEL → SMOOTH → HQ")),
    (("START + B", "Rotate the screen"), ("START + B", "Xoay màn hình")),
    (("START + Y", "Mouse mode on/off (X clicks)"),
     ("START + Y", "Bật/tắt mouse mode (X là click)")),
    (("MENU", "Ask whether to quit the game"),
     ("MENU", "Hỏi có thoát game không")),
]

TROUBLE = [
    (("The D-pad does nothing but the other buttons work",
      "The game is in the wrong phone mode. It is almost certainly set to <b>P</b>, "
      "where the D-pad sends the digits 2/4/6/8 — a game that listens for GameAction "
      "hears nothing. Hold START, tap SELECT until <b>N</b> shows in the corner."),
     ("D-pad không ăn gì trong khi các nút khác vẫn chạy",
      "Game đang sai chế độ máy. Gần như chắc chắn nó đang ở <b>P</b>, mà ở chế độ đó "
      "D-pad gửi ra số 2/4/6/8 — game nào chờ GameAction sẽ không nghe thấy gì. "
      "Giữ START, bấm SELECT tới khi góc màn hiện <b>N</b>.")),
    (("Two games map their buttons differently",
      "That is by design: the phone mode is remembered per game, in "
      "<code>zulu17/bin/config/&lt;game&gt;/game.conf</code>. Set each game once and it sticks. "
      "To reset one, delete its folder there."),
     ("Hai game lại map nút khác nhau",
      "Đó là cố ý: chế độ máy được nhớ riêng cho từng game, trong "
      "<code>zulu17/bin/config/&lt;tên game&gt;/game.conf</code>. Đặt một lần cho mỗi game là xong. "
      "Muốn đưa game nào về mặc định thì xoá thư mục của nó ở đó.")),
    (("The display row in Utilities says OLD and will not open",
      "The emulator on the card is older than the one inside the app — the in-app "
      "update carries the app only, not the 66 MB emulator. From 1.43 the app upgrades "
      "it by itself the next time you open it. Before that, press "
      "<b>Utilities → Install Java Emulator</b>."),
     ("Dòng kiểu hiển thị trong Tiện ích ghi BẢN CŨ và không mở",
      "Giả lập trên thẻ cũ hơn gói trong app — bản cập nhật trong app chỉ mang mã ứng dụng, "
      "không mang 66 MB giả lập. Từ 1.43 app tự nâng cấp ở lần mở kế tiếp. Trước đó thì bấm "
      "<b>Tiện ích → Cài đặt Giả lập Java</b>.")),
    (("A game will not start after you moved it",
      "The system menu caches its game list. RetroHub drops that cache whenever it moves "
      "a game, so use the app's resolution screen rather than moving the file by hand."),
     ("Game không mở được sau khi chuyển thư mục",
      "Menu hệ thống có lưu đệm danh sách game. RetroHub tự xoá đệm đó mỗi khi nó chuyển game, "
      "nên hãy đổi bằng màn độ phân giải trong app thay vì chuyển tay.")),
    (("Rebuilding the emulator lost my saves",
      "Only on 1.41 and earlier: reinstalling wiped the whole runtime folder, and saves live "
      "inside it. Fixed in 1.42 — saves and per-game settings are moved aside and put back."),
     ("Cài lại giả lập làm mất save",
      "Chỉ xảy ra ở 1.41 trở về trước: cài lại xoá cả thư mục giả lập, mà save nằm bên trong đó. "
      "Đã sửa ở 1.42 — save và cấu hình từng game được cất ra rồi đặt lại.")),
]

RES_FOLDERS = ["240320", "320240", "128128", "176208", "640360"]

EXTRA_CSS = """
  .guide h3{margin:30px 0 10px;font-size:1.08rem;color:var(--accent)}
  .guide p{color:var(--muted)}
  .guide p b,.guide li b{color:var(--text)}
  .guide ul{color:var(--muted);padding-left:22px}
  .guide ul li{margin:8px 0}
  .tw{overflow-x:auto;border:1px solid var(--line);border-radius:12px;
    background:var(--panel);margin:18px 0}
  table{border-collapse:collapse;width:100%;font-size:.93rem;min-width:460px}
  th,td{text-align:left;padding:10px 14px;border-bottom:1px solid var(--line);
    vertical-align:top}
  thead th{color:var(--accent);font-size:.82rem;text-transform:uppercase;
    letter-spacing:.05em;white-space:nowrap}
  tbody tr:last-child td{border-bottom:0}
  td:first-child{color:var(--text);font-weight:600;white-space:nowrap}
  td{color:var(--muted)}
  .keys{list-style:none;padding:0;margin:18px 0 0;display:grid;gap:10px;
    grid-template-columns:repeat(auto-fit,minmax(290px,1fr))}
  .keys li{background:var(--panel);border:1px solid var(--line);border-radius:10px;
    padding:12px 15px}
  .keys b{display:block;color:var(--accent);font-size:.95rem;
    font-variant-numeric:tabular-nums}
  .keys span{color:var(--muted);font-size:.88rem}
  .folders{display:flex;gap:9px;flex-wrap:wrap;margin:16px 0 0;padding:0;list-style:none}
  .folders li{background:#0a1120;border:1px solid var(--line);border-radius:8px;
    padding:7px 13px;color:var(--accent);font-size:.92rem}
  .qa{list-style:none;padding:0;margin:0;display:grid;gap:12px}
  .qa li{background:var(--panel);border:1px solid var(--line);border-radius:12px;
    padding:16px 20px}
  .qa b{display:block;margin-bottom:6px}
  .qa span{color:var(--muted);font-size:.94rem}
  .qa code{white-space:normal}
  .toc{list-style:none;padding:0;margin:0;display:flex;flex-wrap:wrap;gap:8px;
    justify-content:center}
  .toc a{display:block;background:var(--panel);border:1px solid var(--line);
    border-radius:999px;padding:7px 15px;color:var(--muted);text-decoration:none;
    font-size:.9rem;transition:border-color .15s,color .15s,background .15s}
  .toc a:hover{border-color:var(--accent-dim);color:var(--text);background:#14243d}
  @media (max-width:600px){ td:first-child{white-space:normal} }
"""

T = {
 "en": {
  "lang": "en", "other": "vi", "other_name": "Tiếng Việt",
  "home": "/", "self": "/java/", "otherself": "/vi/java/",
  "title": "Java J2ME on RetroHub — the guide",
  "desc": ("How to run Java J2ME games on a TrimUI handheld with RetroHub: resolution "
           "folders, phone modes, pad layouts, display modes and where saves live."),
  "keywords": ("RetroHub, J2ME, Java games, FreeJ2ME, TrimUI Brick, TrimUI Brick Pro, "
               "phone mode, key mapping, handheld"),
  "og_desc": ("Resolution folders, phone modes, pad layouts, display modes and saves — "
              "everything needed to run J2ME games well on a TrimUI handheld."),
  "h1": "Java J2ME on RetroHub",
  "lead": ("RetroHub runs J2ME games on FreeJ2ME, straight onto the screen — no RetroArch "
           "and no libretro core involved. This page covers the parts that are not obvious, "
           "starting with the one that confuses everybody: why two games can map their "
           "buttons differently."),
  "back": "Back to the home page",
  "s_cai_dat": ("The emulator is 66 MB and ships inside the app rather than being downloaded, "
                "so it works with no network."),
  "cai_li": [
    "Installed <b>RetroHub-x-full.zip</b>? You already have it. Open "
    "<b>Utilities → Install Java Emulator</b> once and it unpacks.",
    "Installed the lite package? Java is not in it. Download the full one and copy it over "
    "the folder you have — nothing else is lost.",
    "From version 1.43, an emulator older than the one inside the app is upgraded "
    "automatically the next time you open RetroHub. Saves are kept.",
  ],
  "s_thu_muc": ("Every J2ME game was written for one specific handset screen, and the emulator "
                "has no way to guess which. So the folder a game sits in is what tells it: "
                "a jar in <code>Roms/JAVA/240320/</code> is handed a 240×320 canvas."),
  "thu_muc_p2": ("Only about a quarter of the titles in the library state a size in their filename, "
                 "so anything unrecognised lands in <code>240320</code> — the commonest size. If a "
                 "game looks cropped or squashed, it is probably in the wrong folder."),
  "thu_muc_p3": ("To move one: open the game in RetroHub, press the action button and choose "
                 "<b>Resolution</b>. Doing it in the app rather than by hand matters — it also "
                 "clears the system menu's game-list cache, which would otherwise keep pointing "
                 "at the old path."),
  "s_che_do": ("This is the answer to “why does every game map its keys differently”. "
               "J2ME games do not agree on how to read the keypad. Some ask for GameAction "
               "(up/down/left/right/fire), some read the raw digits 2/4/6/8, some use codes "
               "specific to one manufacturer. The emulator has to translate differently for each, "
               "so it carries five phone modes."),
  "che_do_p2": ("The mode is remembered <b>per game</b>, in "
                "<code>zulu17/bin/config/&lt;game&gt;/game.conf</code>. That is why the game you "
                "played yesterday and the one you opened today behave differently — each keeps "
                "its own setting. To change it, hold <b>START</b> and tap <b>SELECT</b> until the "
                "letter you want appears in the corner; it is saved for that game alone."),
  "che_do_note": ("If a game's D-pad does nothing while its other buttons work, it is on <b>P</b>. "
                  "Switch it to <b>N</b>."),
  "s_nut": ("H, K and X are three physical pad layouts. Unlike the phone mode these are global — "
            "one layout for every game. <b>H</b> is the default and is what the five phone modes "
            "P/N/E/S/M all use; picking K or X switches the phone mode to N automatically."),
  "nut_p2": ("Both analog sticks click, and those clicks are L3 and R3 — that is how you reach the "
             "display shortcut. The stick dead zone is 8000 to press and 6000 to release; pushed "
             "diagonally, the emulator takes whichever axis is further from centre so you do not "
             "get two directions flickering."),
  "s_hinh": "Three presets, switchable in the app or in-game.",
  "hinh_li": [
    "<b>PIXEL</b> — nearest-neighbour, no colour blending between pixels, whole-number scale "
    "factors. The one to try first for anything pixel-art.",
    "<b>SMOOTH</b> — linear filtering, fits the largest area that keeps the proportions right. "
    "Can look soft on pixel art.",
    "<b>HQ</b> — asks SDL2 for its best quality. On this driver that is often identical to "
    "SMOOTH, so treat it as experimental.",
  ],
  "hinh_p2": ("In the app: <b>Utilities → Java display mode</b>, which writes the whole preset. "
              "In game: hold <b>START</b> and press <b>R3</b>, which changes the mode and the "
              "integer-scaling flag and leaves the other keys alone. Either way the choice is "
              "saved to <code>renderer.conf</code> and used again next time."),
  "s_toan": ("A 240×320 game is portrait; the Brick Pro panel is 1024×768, landscape. The two "
             "proportions are opposites, so no setting both fills the screen and keeps the "
             "picture honest. Here is what each choice actually gives you."),
  "toan_p2": ("The last two rows are the only ways to genuinely fill the panel without distortion, "
              "and both ask something of you: one asks you to hold the device sideways, the other "
              "only works on games that adapt to the canvas they are given."),
  "s_luu": ("J2ME saves live in <code>Emus/JAVA/zulu17/bin/rms/</code>, one folder per game, and "
            "per-game settings in <code>zulu17/bin/config/</code>."),
  "luu_p2": ("Both sit inside the emulator folder, which is why reinstalling the emulator used to "
             "delete them. Since RetroHub 1.42 they are moved aside before the folder is replaced "
             "and put back afterwards — including when the install fails halfway."),
  "th_button": "Button", "th_h": "Layout H", "th_k": "Layout K", "th_x": "Layout X",
  "th_mode": "Mode", "th_means": "What it means",
  "th_key": "Key", "th_values": "Values", "th_does": "What it does",
  "th_choice": "Choice", "th_size": "Picture size", "th_shape": "Shape", "th_notes": "Notes",
  "h_short": "Shortcut summary",
  "h_exit": "Quitting a game",
  "exit_p": ("Press <b>MENU</b> and a confirmation box appears — the game does not close straight "
             "away. <b>NO</b> is selected by default so a stray press costs nothing. Left or up "
             "picks YES, right or down picks NO, then A or X confirms; B or MENU again cancels. "
             "L3 and R3 are no longer quit buttons."),
  "h_folders": "The five folders",
 },
 "vi": {
  "lang": "vi", "other": "en", "other_name": "English",
  "home": "/vi/", "self": "/vi/java/", "otherself": "/java/",
  "title": "Chơi game Java J2ME trên RetroHub — hướng dẫn",
  "desc": ("Cách chơi game Java J2ME trên máy TrimUI với RetroHub: thư mục độ phân giải, "
           "chế độ máy, bố trí nút, kiểu hiển thị và chỗ lưu save game."),
  "keywords": ("RetroHub, J2ME, game Java, FreeJ2ME, TrimUI Brick, TrimUI Brick Pro, "
               "chế độ máy, gán phím, máy chơi game cầm tay"),
  "og_desc": ("Thư mục độ phân giải, chế độ máy, bố trí nút, kiểu hiển thị và save game — "
              "đủ thứ cần biết để chơi game J2ME cho ra hồn trên máy TrimUI."),
  "h1": "Chơi game Java J2ME trên RetroHub",
  "lead": ("RetroHub chạy game J2ME bằng FreeJ2ME, vẽ thẳng lên màn hình — không qua RetroArch, "
           "không dùng core libretro. Trang này nói những chỗ không hiển nhiên, bắt đầu bằng cái "
           "làm ai cũng thắc mắc: vì sao hai game lại map nút khác nhau."),
  "back": "Về trang chủ",
  "s_cai_dat": ("Bộ giả lập nặng 66 MB và nằm sẵn trong app chứ không phải tải về, nên không có "
                "mạng vẫn cài được."),
  "cai_li": [
    "Đã cài <b>RetroHub-x-full.zip</b>? Máy có sẵn rồi. Vào <b>Tiện ích → Cài đặt Giả lập Java</b> "
    "một lần là nó bung ra.",
    "Đã cài bản gọn? Bản đó không kèm Java. Tải bản đầy đủ rồi chép đè lên thư mục đang có, "
    "không mất gì cả.",
    "Từ bản 1.43, nếu giả lập trên thẻ cũ hơn gói trong app thì app tự nâng cấp ở lần mở kế tiếp. "
    "Save giữ nguyên.",
  ],
  "s_thu_muc": ("Mỗi game J2ME được viết cho đúng một khổ màn điện thoại, mà emulator thì không có "
                "cách nào đoán ra khổ nào. Nên thư mục chứa game chính là chỗ báo cho nó: một file "
                "jar nằm trong <code>Roms/JAVA/240320/</code> sẽ được cấp khung 240×320."),
  "thu_muc_p2": ("Chỉ khoảng một phần tư số game trong kho có ghi kích thước trong tên file, nên game "
                 "nào không nhận ra được sẽ vào <code>240320</code> — khổ phổ biến nhất. Thấy game bị "
                 "cắt xén hay méo mó thì phần nhiều là đang nằm sai thư mục."),
  "thu_muc_p3": ("Muốn chuyển: mở game trong RetroHub, bấm nút thao tác rồi chọn <b>Độ phân giải</b>. "
                 "Làm trong app khác với chuyển tay ở chỗ nó xoá luôn bộ nhớ đệm danh sách game của "
                 "menu hệ thống — không xoá thì menu vẫn trỏ vào đường dẫn cũ."),
  "s_che_do": ("Đây là câu trả lời cho “sao mỗi game lại map phím một kiểu”. Game J2ME không "
               "thống nhất cách đọc bàn phím. Có game hỏi GameAction (lên/xuống/trái/phải/bắn), có game "
               "đọc thẳng số 2/4/6/8, có game dùng mã riêng của một hãng. Emulator buộc phải dịch khác "
               "nhau cho từng loại, nên nó mang sẵn năm chế độ máy."),
  "che_do_p2": ("Chế độ được nhớ <b>riêng cho từng game</b>, trong "
                "<code>zulu17/bin/config/&lt;tên game&gt;/game.conf</code>. Đó là lý do game chơi hôm qua "
                "và game mở hôm nay lại khác nhau — mỗi game giữ cài đặt của nó. Muốn đổi thì giữ "
                "<b>START</b> rồi bấm <b>SELECT</b> tới khi góc màn hiện chữ mình muốn; nó chỉ lưu cho "
                "riêng game đó."),
  "che_do_note": ("Game nào D-pad không ăn gì mà các nút khác vẫn chạy thì nó đang ở <b>P</b>. "
                  "Chuyển sang <b>N</b>."),
  "s_nut": ("H, K và X là ba bố trí nút vật lý. Khác với chế độ máy, ba cái này dùng chung — một bố trí "
            "cho mọi game. <b>H</b> là mặc định, và cả năm chế độ máy P/N/E/S/M đều dùng nó; chọn K hay X "
            "thì chế độ máy tự chuyển về N."),
  "nut_p2": ("Hai cần analog đều bấm lún xuống được, và cú bấm đó chính là L3 với R3 — đường để dùng tổ "
             "hợp đổi hình ảnh. Vùng chết của cần là 8000 để tính nhấn và 6000 để tính nhả; đẩy chéo thì "
             "emulator lấy trục nào lệch tâm nhiều hơn, để không bị rung hai hướng."),
  "s_hinh": "Ba preset, đổi được trong app hoặc ngay trong game.",
  "hinh_li": [
    "<b>PIXEL</b> — nearest-neighbor, không trộn màu giữa hai pixel, hệ số phóng là số nguyên. "
    "Nên thử đầu tiên với game pixel-art.",
    "<b>SMOOTH</b> — lọc linear, lấp vùng lớn nhất mà vẫn giữ đúng tỉ lệ. Có thể hơi mềm với pixel-art.",
    "<b>HQ</b> — xin SDL2 mức chất lượng tốt nhất. Trên driver này thường ra y hệt SMOOTH, nên coi như "
    "còn thử nghiệm.",
  ],
  "hinh_p2": ("Trong app: <b>Tiện ích → Kiểu hiển thị game Java</b>, ghi trọn cả preset. Trong game: giữ "
              "<b>START</b> bấm <b>R3</b>, đổi kiểu hiển thị cùng cờ phóng nguyên và không đụng các khoá "
              "còn lại. Đằng nào lựa chọn cũng được ghi vào <code>renderer.conf</code> và dùng lại lần sau."),
  "s_toan": ("Game 240×320 là khổ dựng đứng; màn Brick Pro là 1024×768, nằm ngang. Hai tỉ lệ ngược nhau, "
             "nên không cấu hình nào vừa lấp kín màn vừa giữ hình cho thật. Đây là cái mỗi lựa chọn thật "
             "sự cho ra."),
  "toan_p2": ("Hai dòng cuối là hai cách duy nhất lấp kín màn mà không méo, và cả hai đều đòi hỏi thứ gì "
              "đó: một cái bắt cầm máy nằm ngang, một cái chỉ ăn với game biết tự co giãn theo khung được "
              "cấp."),
  "s_luu": ("Save game J2ME nằm ở <code>Emus/JAVA/zulu17/bin/rms/</code>, mỗi game một thư mục, còn cấu "
            "hình riêng từng game ở <code>zulu17/bin/config/</code>."),
  "luu_p2": ("Cả hai nằm bên trong thư mục giả lập, nên trước đây cài lại giả lập là xoá mất. Từ RetroHub "
             "1.42 chúng được cất ra chỗ khác trước khi thay thư mục rồi đặt lại — kể cả khi bản cài hỏng "
             "giữa chừng."),
  "th_button": "Nút", "th_h": "Bố trí H", "th_k": "Bố trí K", "th_x": "Bố trí X",
  "th_mode": "Chế độ", "th_means": "Nghĩa là gì",
  "th_key": "Khoá", "th_values": "Giá trị", "th_does": "Tác dụng",
  "th_choice": "Cách", "th_size": "Cỡ hình", "th_shape": "Tỉ lệ", "th_notes": "Ghi chú",
  "h_short": "Tóm tắt phím tắt",
  "h_exit": "Thoát game",
  "exit_p": ("Bấm <b>MENU</b> sẽ hiện hộp xác nhận — game không thoát ngay. Mặc định con trỏ nằm ở "
             "<b>NO</b> để bấm nhầm cũng không sao. Trái hoặc lên chọn YES, phải hoặc xuống chọn NO, rồi "
             "A hay X để xác nhận; B hoặc MENU lần nữa là huỷ. L3 và R3 không còn là lệnh thoát."),
  "h_folders": "Năm thư mục",
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
<link rel="alternate" hreflang="en" href="{DOMAIN}/java/">
<link rel="alternate" hreflang="vi" href="{DOMAIN}/vi/java/">
<link rel="alternate" hreflang="x-default" href="{DOMAIN}/java/">
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
    <p class="sub" style="max-width:760px;margin:0 auto 26px">{lead}</p>
    <ul class="toc">{toc}</ul>
  </div>
</header>

<main class="wrap guide">

  <section id="cai-dat" class="rise" style="padding-top:26px">
    <h2>{s_cai_dat_h}</h2>
    <p>{s_cai_dat}</p>
    <ul>{cai_li}</ul>
  </section>

  <section id="thu-muc" class="rise">
    <h2>{s_thu_muc_h}</h2>
    <p>{s_thu_muc}</p>
    <h3>{h_folders}</h3>
    <ul class="folders">{folders}</ul>
    <p>{thu_muc_p2}</p>
    <p>{thu_muc_p3}</p>
  </section>

  <section id="che-do-may" class="rise">
    <h2>{s_che_do_may_h}</h2>
    <p>{s_che_do}</p>
    <div class="tw"><table>
      <thead><tr><th>{th_mode}</th><th>{th_means}</th></tr></thead>
      <tbody>{phonerows}</tbody>
    </table></div>
    <p>{che_do_p2}</p>
    <p class="note">{che_do_note}</p>
  </section>

  <section id="nut-bam" class="rise">
    <h2>{s_nut_bam_h}</h2>
    <p>{s_nut}</p>
    <div class="tw"><table>
      <thead><tr><th>{th_button}</th><th>{th_h}</th><th>{th_k}</th><th>{th_x}</th></tr></thead>
      <tbody>{padrows}</tbody>
    </table></div>
    <p>{nut_p2}</p>
    <h3>{h_short}</h3>
    <ul class="keys">{shortcuts}</ul>
    <h3>{h_exit}</h3>
    <p>{exit_p}</p>
  </section>

  <section id="hinh-anh" class="rise">
    <h2>{s_hinh_anh_h}</h2>
    <p>{s_hinh}</p>
    <ul>{hinh_li}</ul>
    <p>{hinh_p2}</p>
    <div class="tw"><table>
      <thead><tr><th>{th_key}</th><th>{th_values}</th><th>{th_does}</th></tr></thead>
      <tbody>{confrows}</tbody>
    </table></div>
  </section>

  <section id="toan-man-hinh" class="rise">
    <h2>{s_toan_man_hinh_h}</h2>
    <p>{s_toan}</p>
    <div class="tw"><table>
      <thead><tr><th>{th_choice}</th><th>{th_size}</th><th>{th_shape}</th><th>{th_notes}</th></tr></thead>
      <tbody>{fitrows}</tbody>
    </table></div>
    <p>{toan_p2}</p>
  </section>

  <section id="luu-game" class="rise">
    <h2>{s_luu_game_h}</h2>
    <p>{s_luu}</p>
    <p>{luu_p2}</p>
  </section>

  <section id="su-co" class="rise">
    <h2>{s_su_co_h}</h2>
    <ul class="qa">{trouble}</ul>
  </section>

  <section class="rise">
    <p style="margin-top:34px">
      <a class="btn ghost" href="{home}">{back}</a>
      <a class="btn ghost" href="https://t.me/retrohubtool" style="margin-left:10px">{join}</a>
    </p>
  </section>

</main>

<script>
  // Same reveal-on-scroll as the landing page, and the same escape hatch for
  // anyone who has asked their system not to animate things.
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


def pick(pair, lang):
    """One row of the bilingual tables."""
    return pair[0] if lang == "en" else pair[1]


def render(lang):
    t = T[lang]
    canon = DOMAIN + t["self"]
    idx = 1 if lang == "en" else 2

    # The top menu is the site's, not this page's - same items, same order, from
    # one function in build.py so the two cannot drift. The page's own sections
    # move into a table of contents under the heading, where they are still one
    # click away without competing with the site menu.
    navlinks = navlinks_for(lang, "java")
    toc = "".join('<li><a href="#%s">%s</a></li>' % (sec[0], sec[idx])
                  for sec in SECTIONS)
    folders = "".join("<li>%s</li>" % f for f in RES_FOLDERS)
    cai_li = "".join("<li>%s</li>" % s for s in t["cai_li"])
    hinh_li = "".join("<li>%s</li>" % s for s in t["hinh_li"])
    padrows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % pick(r, lang)
        for r in PAD_ROWS)
    phonerows = "".join("<tr><td>%s</td><td>%s</td></tr>" % pick(r, lang)
                        for r in PHONE_ROWS)
    confrows = "".join(
        "<tr><td><code>%s</code></td><td>%s</td><td>%s</td></tr>" % pick(r, lang)
        for r in CONF_ROWS)
    fitrows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % pick(r, lang)
        for r in FIT_ROWS)
    shortcuts = "".join("<li><b>%s</b><span>%s</span></li>" % pick(r, lang)
                        for r in SHORTCUTS)
    trouble = "".join("<li><b>%s</b><span>%s</span></li>" % pick(r, lang)
                      for r in TROUBLE)

    ld = {
        "@context": "https://schema.org", "@type": "TechArticle",
        "headline": t["title"], "description": t["desc"], "inLanguage": lang,
        "url": canon, "author": {"@type": "Person", "name": "Nguyễn Xuân Hòa",
                                 "url": "https://xuanhoa493.com"},
        "isPartOf": {"@type": "WebSite", "name": "RetroHub", "url": DOMAIN},
    }

    out = PAGE
    fill = {
        "lang": lang, "canon": canon, "DOMAIN": DOMAIN,
        "oglocale": "en_US" if lang == "en" else "vi_VN",
        "ldjson": json.dumps(ld, ensure_ascii=False, indent=2),
        "css": CSS, "extracss": EXTRA_CSS, "navlinks": navlinks,
        "toc": toc, "folders": folders, "cai_li": cai_li, "hinh_li": hinh_li,
        "padrows": padrows, "phonerows": phonerows, "confrows": confrows,
        "fitrows": fitrows, "shortcuts": shortcuts, "trouble": trouble,
        "join": "Ask in the Telegram group" if lang == "en" else "Hỏi trong nhóm Telegram",
    }
    # Section headings come from the same table the nav is built from, so a
    # renamed section cannot end up with a nav label that says something else.
    for sid, en, vi in SECTIONS:
        fill["s_%s_h" % sid.replace("-", "_")] = en if lang == "en" else vi

    for k, v in fill.items():
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
        path = os.path.join(ROOT, "java/index.html" if lang == "en"
                            else "vi/java/index.html")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(render(lang))
        print("  %-22s %6d byte" % (os.path.relpath(path, ROOT), os.path.getsize(path)))


if __name__ == "__main__":
    main()
