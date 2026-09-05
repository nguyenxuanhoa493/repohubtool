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
    ("1.70", "2026-09-05",
     ("YouTube: Refine card and thumbnail dimensions to perfectly fit screen width with balanced padding",
      "YouTube: Tinh chỉnh kích thước thumbnail và thẻ lớn hơn, vừa vặn tuyệt đối với chiều rộng màn hình"),
     [("Larger immersive thumbnails: increased card width to 390px (Smart Pro) and 316px (Brick), providing larger 16:9 thumbnails while keeping clean 24-37px edge margins.",
       "Thumbnail lớn hơn, hình ảnh sống động: tăng chiều rộng thẻ lên 390px (Smart Pro) và 316px (Brick) giúp ảnh bìa 16:9 to rõ nét, lề trái phải vừa vặn 24-37px không bị quá hẹp hay quá rộng."),
      ("Extended title readability: expanded maximum visible title length up to 34 characters to display full video titles without premature truncation.",
       "Hiển thị tiêu đề dài hơn: mở rộng độ dài tiêu đề hiển thị tối đa lên đến 34 ký tự giúp đọc trọn vẹn tên bài hát và video rõ ràng.")]),

    ("1.69", "2026-09-05",
     ("YouTube: Default Music/KPOP/USUK/Tiktok presets, Favorites tab, keyword deletion, clean responsive thumbnails & load more",
      "YouTube: Mặc định Music, KPOP, USUK, Tiktok; tab Yêu thích; xóa từ khóa; thumbnail vừa vặn không tràn viền và tải thêm video"),
     [("New default topic presets: changed default keywords to Music (default), KPOP, USUK, Tiktok, preserving natural YouTube ranking without artificial year or age sorting.",
       "Bộ từ khóa mặc định mới: chuyển từ khóa sang Music (mặc định), KPOP, USUK, Tiktok, giữ nguyên thứ hạng tự nhiên từ YouTube, bỏ hoàn toàn logic nối năm và lọc ngày."),
      ("Favorites management: press [Y] on any video to add/remove from Favorites with heart badge indicator. When favorite videos exist, YouTube opens directly to the Favorites tab by default.",
       "Quản lý danh sách Yêu thích: bấm [Y] trên video bất kỳ để thêm/bỏ Yêu thích (có huy hiệu tim đỏ ♥). Nếu có dữ liệu, app sẽ tự động hiển thị tab Yêu thích đầu tiên khi mở menu YouTube."),
      ("Delete custom keywords: press SELECT [SL] while browsing custom search keywords to easily remove unwanted history queries from the pill navigation bar.",
       "Nút xóa từ khóa tìm kiếm: bấm phím SELECT [SL] khi đang ở tab từ khóa tùy chỉnh để xóa bỏ từ khóa khỏi lịch sử tìm kiếm nhanh chóng."),
      ("Responsive compact thumbnails: reduced card and thumbnail dimensions to fit both TrimUI Brick (1024x768) and Smart Pro (1280x720) perfectly without horizontal overflow or screen clipping.",
       "Thumbnail gọn gàng, chống tràn màn hình: thu nhỏ kích thước thẻ và thumbnail 16:9 vừa vặn tuyệt đối cho cả màn hình TrimUI Brick (1024x768) và Smart Pro (1280x720), không còn bị tràn ra ngoài biên."),
      ("Clean single-line title: removed channel name and upload date lines for a clutter-free, modern, and readable card interface.",
       "Giao diện tối giản, thoáng mắt: lược bỏ hoàn toàn tên kênh và thời gian đăng video, tập trung vào thumbnail và tiêu đề rõ nét."),
      ("Load more pagination card: added a dedicated 'Load more videos' card at the end of the list powered by InnerTube continuation tokens, allowing endless browsing of video feeds.",
       "Thẻ tải thêm video ở cuối danh sách: tích hợp thẻ 'Tải thêm' ở cuối danh sách video thông qua continuation token của YouTube InnerTube, cho phép tải thêm video liên tục tiện lợi.")]),

    ("1.68", "2026-09-05",
     ("Optimize YouTube menu: instant load via feed cache, parallel thumbnail prefetch, and rock-solid 60 FPS",
      "Tối ưu menu YouTube: mở tức thì qua feed cache, tải song song thumbnail và duy trì 60 FPS mượt mà"),
     [("Persistent feed cache: trending videos and keywords are cached on SDCARD so opening the menu or switching tabs loads instantly with 0 latency.",
       "Bộ nhớ đệm dữ liệu lâu dài: danh sách video thịnh hành và từ khóa được lưu trực tiếp trên thẻ nhớ, giúp mở menu hoặc chuyển danh mục xuất hiện ngay lập tức không cần chờ mạng."),
      ("Parallel prioritized thumbnails: front-page visible video thumbnails download concurrently with 3 workers, cutting thumbnail loading time from 7s down to ~0.5s.",
       "Tải trước thumbnail song song theo mức ưu tiên: 6 video đang hiển thị trên màn hình được tải đồng thời với 3 luồng mạng, rút ngắn thời gian nạp ảnh bìa từ 7 giây xuống chỉ còn ~0.5 giây."),
      ("Eliminated continuation request overhead: avoid redundant second network pagination request when the first page already yields sufficient candidate videos, doubling search speed.",
       "Loại bỏ request mạng dư thừa: không gọi thêm yêu cầu phân trang thứ hai khi trang đầu tiên đã có đủ video cho lưới 3x2, tăng gấp đôi tốc độ tải mạng từ 4-5s xuống ~1.5s."),
      ("Rock-solid 60 FPS rendering: throttled texture decoding to 1 image per frame and replaced filesystem stat calls with in-memory set lookups, eliminating all stutter when scrolling.",
       "Duy trì 60 FPS mượt mà tuyệt đối: giới hạn giải mã tối đa 1 texture mỗi khung hình và loại bỏ hoàn toàn lệnh kiểm tra ổ đĩa trong vòng lặp vẽ, giúp thao tác bấm cuộn lướt video mượt như bơ."),
      ("CPU overload prevention: delayed speculative stream pre-fetching until the user pauses on a video for 2.5s, freeing CPU cores for responsive UI navigation.",
       "Chống nghẽn CPU Allwinner: dời tính năng tự động dò luồng phát chỉ khi người dùng dừng lại xem video quá 2.5 giây, giải phóng CPU để giao diện luôn phản hồi phím bấm tức thì.")]),

    ("1.67", "2026-09-05",
     ("Fix new LED themes: continuous vibrant strobe & pulse, auto-restart daemon to load new effects",
      "Khắc phục triệt để lỗi theme LED mới: tối ưu nháy sáng liên tục, tự khởi động lại daemon nạp hiệu ứng mới"),
     [("Redesigned high-energy effects: eliminated pitch-black dead times and 30ms aliasing dropouts in strobe, lightning, pulse_bass, hyper_chase, and chaos. All effects now maintain a rich ambient energy floor with blazing bursts.",
       "Thiết kế lại 5 hiệu ứng LED sôi động: loại bỏ hoàn toàn tình trạng đèn bị tối đen kéo dài và lỗi mất khung hình ở 30 FPS. Các hiệu ứng strobe, sấm sét, bass drop, drift và glitch giờ duy trì nền ánh sáng sống động liên tục cùng các luồng chớp/sóng xung kích bốc lửa."),
      ("Hardware write order fix: corrected sysfs driver latch sequence in leddaemon to write color before triggering static effect, ensuring every single frame renders accurately on hardware.",
       "Sửa thứ tự kích hoạt driver phần cứng: đảo lại thứ tự ghi màu trước rồi mới kích hoạt chốt effect STATIC trong sysfs, giúp phần cứng LED nhận diện và chuyển màu chính xác từng khung hình."),
      ("Auto-restart stale background daemon: automatically stop and restart the LED background process upon update and theme selection so newly published effects load immediately into RAM without requiring a reboot.",
       "Tự động khởi động lại tiến trình daemon: tự động tắt và khởi động lại tiến trình chạy ngầm LED khi cập nhật hoặc chọn theme, giúp bộ nhớ nạp ngay hiệu ứng mới nhất mà không bị giữ lại code cũ trong RAM.")]),

    ("1.66", "2026-09-05",
     ("Fix infinite OTA update loop for Java runtime (JM 1.0.5) and optimize startup checks",
      "Sửa triệt để lỗi lặp cập nhật OTA giả lập Java J2ME (JM 1.0.5) và tối ưu kiểm tra runtime"),
     [("Prevent startup payload overwrite: fixed runtime_is_stale() incorrectly wiping JM 1.0.5 with legacy bundled payload on application startup.",
       "Ngăn chặn ghi đè khi khởi động: khắc phục lỗi runtime_is_stale() ngộ nhận và tự động bung gói payload cũ đè lên bản mới JM 1.0.5 mỗi khi mở app."),
      ("Dynamic user config exclusion: removed mutable graphics.cfg from static hash verification in manifest so in-game display mode changes do not trigger false-positive updates.",
       "Tách biệt tệp cấu hình động: loại bỏ graphics.cfg khỏi danh sách kiểm tra hash tĩnh trong manifest để việc đổi chế độ hiển thị trong game không bị hiểu nhầm là có bản cập nhật mới.")]),

    ("1.65", "2026-09-05",
     ("Update Java J2ME emulator (JM 1.0.5): on-screen text input, diagonal D-pad, hotkeys, display mode toggle",
      "Cập nhật giả lập Java J2ME (JM 1.0.5): bàn phím ảo gõ chữ, D-pad chéo, phím tắt 1/3/7/9, đổi chế độ hiển thị"),
     [("Upstream JM fork by nvcuong1312: integrated the latest JM 1.0.5 build (https://github.com/nvcuong1312/jm) with dedicated optimizations for TrimUI handhelds. Check the full Java guide at /java/ for controls, display modes and source credits.",
       "Bản phân nhánh JM bởi nvcuong1312: tích hợp bản dựng JM 1.0.5 mới nhất (https://github.com/nvcuong1312/jm) tối ưu riêng cho máy cầm tay TrimUI. Xem hướng dẫn phím bấm, chế độ hiển thị và ghi nhận nguồn tại /vi/java/."),
      ("On-screen virtual keyboard: games requiring character or text input now support interactive typing via font.ttf (* to delete, # to add, 2/4 for letters, 1/3 for digits, 7/9 for special characters).",
       "Bàn phím ảo nhập text: game Java yêu cầu nhập tên nhân vật/text giờ đã có bàn phím ảo hiển thị trực quan qua font.ttf (* xóa ký tự, # thêm ký tự, 2/4 chọn chữ a-z, 1/3 chọn số 0-9, 7/9 ký tự đặc biệt)."),
      ("Diagonal D-pad & hotkey shortcuts: full 8-direction D-pad support, and pressing Menu + D-pad Left toggles diagonal directions to send number keys 1, 3, 7, 9.",
       "D-pad hướng chéo và phím tắt nhanh: D-pad hỗ trợ đầy đủ 8 hướng chéo, bấm tổ hợp Menu + D-pad Trái để chuyển nhanh các hướng chéo thành các phím số 1, 3, 7, 9."),
      ("In-game display mode toggle: press Select during gameplay to instantly switch between linear (smooth) and nearest (pixel) scaling, automatically synchronized with RetroHub display settings.",
       "Đổi chế độ hiển thị tức thì trong game: bấm phím Select khi đang chơi để chuyển đổi giữa hai chế độ Linear (mịn) và Nearest (pixel sắc nét), tự động đồng bộ cùng cài đặt RetroHub.")]),

    ("1.64", "2026-09-05",
     ("Add 5 high-energy LED effects (rave strobe, thunderstorm, bass drop) and 7 vibrant themes",
      "Bổ sung 5 hiệu ứng LED sôi động (chớp giật strobe, bão sấm sét, bass drop...) và 7 theme LED mới"),
     [("5 new mathematical LED effects: strobe (fast double-flash rave party), lightning (intermittent violent thunderstorm flash), pulse_bass (130 BPM subwoofer shockwave), hyper_chase (speed racer comet trail), and chaos (cyber glitch).",
       "5 hiệu ứng LED toán học tốc độ cao: strobe (vũ trường EDM chớp kép trái/phải liên tục), lightning (bão sấm sét chùm tia chớp gắt), pulse_bass (đập bass EDM 130 BPM lan toả từ tâm), hyper_chase (đua xe vệt lửa siêu tốc) và chaos (glitch loạn nhịp arcade)."),
      ("7 dynamic LED themes: EDM Rave, Bass Drop, Thunderstorm, Cyber Glitch, Night Drift, Red Alert, and Supernova, available immediately in Settings > LED Lights.",
       "7 bộ theme LED mới cực cháy: Vũ trường EDM, Bass Drop, Bão sấm sét, Cyber Glitch, Đua xe Drift, Báo động đỏ và Siêu tân tinh; chọn và xem thử trực quan trong Cài đặt > Đèn LED.")]),

    ("1.63", "2026-09-05",
     ("Support TrimUI Smart Pro S (TSPS) and multi-device SDL2 library search",
      "Hỗ trợ máy mới TrimUI Smart Pro S (TSPS), tối ưu tìm nạp thư viện SDL2 đa hệ máy"),
     [("TrimUI Smart Pro S (TSPS) compatibility: resolved startup black screen by searching /usr/lib and /usr/lib64 when /usr/trimui/lib is absent.",
       "Tương thích TrimUI Smart Pro S (TSPS): khắc phục lỗi sập màn hình đen khi khởi động bằng cách tự động nạp thư viện từ /usr/lib và /usr/lib64 khi máy không có /usr/trimui/lib."),
      ("Multi-platform fallback chain: prioritized tailored libraries for Brick/Smart Pro while supporting standard 64-bit handhelds and bundled libs in libs/.",
       "Chuỗi nạp thư viện đa nền tảng: ưu tiên bản SDL2 tùy biến riêng cho TrimUI Brick / Smart Pro, đồng thời sẵn sàng tương thích các bản Linux handheld 64-bit và thư mục libs/ đi kèm.")]),

    ("1.62", "2026-09-05",
     ("Direct hotkey controls for exit modal: [B] Exit completely, [A] Stay",
      "Tối ưu thao tác hộp thoại xác nhận thoát: bấm [B] Thoát hẳn, [A] Ở lại trực tiếp"),
     [("Instant hotkey actions: eliminated multi-step D-pad selection; pressing button [B] immediately quits the application, while button [A] instantly returns to the app.",
       "Thao tác phím trực tiếp: loại bỏ bước điều hướng D-pad qua lại rườm rà; bấm ngay phím [B] để thoát hẳn ứng dụng, hoặc phím [A] để ở lại ngay lập tức."),
      ("Visual action buttons: distinct dedicated styling for each action ([A] Stay in green, [B] Exit completely in red) with clear instructional subtitles.",
       "Giao diện nút trực quan: hiển thị rõ ràng 2 nút hành động với màu sắc đặc trưng ([A] Ở lại màu xanh lá, [B] Thoát hẳn màu đỏ) kèm phụ đề hướng dẫn thao tác dứt khoát.")]),

    ("1.61", "2026-09-05",
     ("Exit confirmation modal on home screen to prevent accidental quitting",
      "Thêm hộp thoại xác nhận thoát ứng dụng ở menu chính để tránh bấm nhầm"),
     [("Exit confirmation modal: pressing button X (or button B, or selecting 'Exit' from the main menu) now opens an interactive confirmation dialog instead of quitting abruptly.",
       "Hộp thoại xác nhận thoát ứng dụng: khi bấm phím X (hoặc phím B, hoặc chọn mục 'Thoát' ở menu chính), ứng dụng sẽ mở hộp thoại xác nhận thay vì đóng đột ngột."),
      ("Dual action buttons: provides '[B] Stay' (highlighted by default to prevent accidental exits) and '[A] Exit', with D-pad navigation and one-tap cancellation.",
       "Hai nút điều hướng tiện lợi: hỗ trợ nút '[B] Ở lại' (được chọn mặc định tránh bấm nhầm) và '[A] Thoát', điều hướng linh hoạt bằng phím điều hướng D-pad."),
      ("Home footer navigation hint: displays explicit '[A] Select / Open' and '[X] Exit' shortcuts on the home screen footer bar.",
       "Chỉ dẫn chân trang trực quan: hiển thị rõ ràng hai phím tắt '[A] Chọn / Mở' và '[X] Thoát' ngay tại thanh điều hướng chân trang menu chính.")]),

    ("1.60", "2026-09-05",
     ("Smooth YouTube playback: zero screen flicker when connecting, real-time video sorting, and speculative preload",
      "Trải nghiệm YouTube mượt mà: kết nối nguồn phát không nháy màn hình, sắp xếp video mới nhất và tải trước thông minh"),
     [("Zero screen flicker: completely silenced yt-dlp console tty output and implemented smooth double-buffered splash handoff to RetroArch.",
       "Chấm dứt hoàn toàn hiện tượng nháy màn hình: tắt luồng in tty console của yt-dlp và chuyển giao màn hình sạch sang RetroArch trên cả hai bộ đệm (Double-Buffer VSync)."),
      ("Non-blocking 60 FPS stream connecting modal: asynchronous background stream extraction with a breathing pulse dialog, supporting instant cancellation with button B.",
       "Hộp thoại kết nối luồng phát chạy ngầm 60 FPS: trích xuất luồng trên luồng riêng với giao diện phát sáng nhịp thở mượt mà, hỗ trợ bấm phím B để hủy kết nối."),
      ("Real-time chronological sorting: extracts publication timestamps and sorts candidates by age in hours, guaranteeing the newest videos (hours/days ago) always appear at the top.",
       "Sắp xếp video theo thời gian thực: bóc tách thời gian tải lên và tính toán độ tuổi video theo giờ, đảm bảo các video mới nhất (vài giờ/vài ngày trước) luôn nằm trên đầu danh sách."),
      ("Trending categories and speculative preload: MV Vpop, Nhạc hot tiktok, Hot girl tiktok, MV Kpop, with automatic background prefetching of adjacent keywords and thumbnails.",
       "Bộ từ khóa thịnh hành mới và tải trước lân cận: MV Vpop, Nhạc hot tiktok, Hot girl tiktok, MV Kpop; tự động nạp trước kết quả và thumbnail của 2 tab xung quanh dưới nền.")]),

    ("1.59", "2026-09-05",
     ("Comprehensive YouTube upgrade: chronological sorting, speculative preloading, and non-blocking HUD",
      "Nâng cấp toàn diện YouTube: sắp xếp video mới nhất, tải trước thông minh và thanh tải HUD không chặn"),
     [("Real-time chronological sorting: extracts publication timestamps and sorts candidates by age in hours, guaranteeing the newest videos (hours/days ago) always appear at the top.",
       "Sắp xếp video theo thời gian thực: bóc tách thời gian tải lên và tính toán độ tuổi video theo giờ, đảm bảo các video mới nhất (vài giờ/vài ngày trước) luôn nằm trên đầu danh sách."),
      ("Updated trending preset categories to MV Vpop, Nhạc hot tiktok, Hot girl tiktok, MV Kpop, with automatic background current year query targeting.",
       "Cập nhật 4 bộ từ khóa thịnh hành chuẩn xu hướng: MV Vpop, Nhạc hot tiktok, Hot girl tiktok, MV Kpop (tự động gắn năm 2026 khi truy vấn ngầm)."),
      ("Speculative tab preloading: background prefetching of adjacent keywords and thumbnails eliminates switching delays between tabs.",
       "Tải trước từ khóa lân cận: tự động nạp trước kết quả tìm kiếm và ảnh bìa của 2 tab xung quanh dưới nền, giúp chuyển từ khóa tức thì không độ trễ."),
      ("Non-blocking async search: background thread fetching with a smooth glowing bottom HUD banner replaces the UI freeze.",
       "Tìm kiếm bất đồng bộ không chặn: tiến trình nạp dữ liệu chạy ngầm kèm thanh trạng thái HUD phát sáng ở đáy màn hình thay vì làm đơ giao diện."),
      ("Publication age badge: video cards now display relative upload times (e.g. Channel • 2 days ago) alongside the channel name.",
       "Hiển thị thời gian đăng video: thông tin thẻ video hiển thị chi tiết 'Tên Kênh • X ngày trước' giúp nhận biết trực quan độ mới của clip.")]),

    ("1.58", "2026-09-05",
     ("Blazing fast game library: 60 FPS scrolling, lazy boxarts, and instant sorting in RAM",
      "Tối ưu siêu tốc kho game: cuộn 60 FPS mượt mà, tải ảnh bìa thông minh và sắp xếp tức thì trong RAM"),
     [("Display item caching and lazy boxart resolution eliminate per-frame FAT32 SD card filesystem scans, restoring smooth 60 FPS scrolling even with thousands of ROMs.",
       "Cơ chế lưu cache danh sách và phân giải ảnh bìa theo nhu cầu (lazy boxart) loại bỏ hoàn toàn các lệnh quét tệp tin trên thẻ nhớ SD, duy trì tốc độ cuộn 60 FPS mượt mà ngay cả với kho hàng ngàn ROM."),
      ("Toggling between downloads and A-Z sorting, or jumping with the Alphabet modal (Y button), is now performed in RAM using fast C-level Timsort in under 2ms.",
       "Chuyển đổi sắp xếp (Lượt tải <-> A-Z) và mở Bảng chữ cái A-Z (phím Y) được xử lý trực tiếp trong RAM với thuật toán Timsort cực nhanh dưới 2ms thay vì quét lại SQLite trên thẻ nhớ."),
      ("Optimized SQLite engine: removed unused mirror count subqueries, enabled 8MB RAM page cache and 32MB memory-mapped I/O, and added B-tree indexes.",
       "Tối ưu hóa SQLite: loại bỏ các câu truy vấn đếm mirror thừa, bật bộ nhớ đệm RAM 8MB và mmap I/O 32MB, cùng hệ thống chỉ mục B-tree giúp tăng tốc tìm kiếm và lọc game."),
      ("Real-time badge updates for active downloads are now dynamically checked only for the visible screen items.",
       "Cập nhật huy hiệu trạng thái tải game theo thời gian thực chỉ quét trên các dòng đang hiển thị trong khung nhìn, đảm bảo phản hồi tức thì mà không tốn tài nguyên.")]),

    ("1.57", "2026-09-04",
     ("Major YouTube playback speedup: RAM tmpfs, speculative pre-fetch, and instant loading dialog",
      "Tối ưu đột phá tốc độ phát YouTube: RAM tmpfs, nạp trước thông minh (Pre-fetch) và hộp thoại tải"),
     [("Speculative background pre-fetch resolves video stream URLs instantly as you browse cards, cutting playback start time to 0.0009s.",
       "Cơ chế nạp trước thông minh (Speculative Pre-fetch) tự động tải sẵn link phát khi rê con trỏ, đưa thời gian mở video xuống còn 0,0009 giây."),
      ("yt-dlp is pre-extracted into RAM tmpfs (<code>/tmp/ytdlp_cache</code>) on startup, eliminating slow SD card zip decompression bottlenecks.",
       "yt-dlp được giải nén sẵn vào phân vùng RAM ảo (<code>/tmp/ytdlp_cache</code>) ngay khi mở menu, loại bỏ hoàn toàn độ trễ đọc file zip từ thẻ nhớ."),
      ("Added an instant loading dialog with real-time video title and status, replacing the old black screen freeze.",
       "Hiển thị hộp thoại trạng thái trực quan với tựa đề video ngay khi bấm phím A, chấm dứt tình trạng đen màn hình khi kết nối luồng phát."),
      ("Removed failing proxy endpoints and optimized single-client Android extraction.",
       "Loại bỏ các cổng proxy ngoài không ổn định và tối ưu bộ phân giải Android trực tiếp.")]),

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
