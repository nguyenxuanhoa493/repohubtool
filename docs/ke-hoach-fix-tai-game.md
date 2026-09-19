# Kế hoạch sửa lỗi: tải game & màn chi tiết

Phạm vi: luồng tải game (hàng chờ, tiến trình, huỷ, giải nén, đặt ROM vào
`Roms/`) và màn chi tiết game + danh sách store ở phần "game đã tải".
Ngoài phạm vi: store theme/icon/giả lập, YouTube, netplay, LED, updater.

## 1. Nguyên tắc

1. Tái hiện bằng harness headless trước khi sửa, chạy lại harness sau khi sửa.
2. Mỗi đợt một commit riêng; không trộn nhóm lỗi vào nhau.
3. Giữ tương thích: thêm khoá mới vào `dl_state` thay vì đổi khoá cũ; i18n chỉ
   thêm key, không đổi key đang dùng.
4. Thay đổi "đã tải" theo hướng thêm nhánh fallback, không thay logic cũ.
5. Trước khi lên sóng: chạy `python tools/make_release.py` (step 1-5) trong CI
   hoặc WSL. Guard step 3 chặn nếu chạy trên checkout Windows CRLF.

## 2. Danh sách lỗi đã xác minh

| ID | Mức | Lỗi | Vị trí |
|----|-----|-----|--------|
| P0-1 | Chặn | Slot tải không nhả sau lần tải foreground xong; mọi lượt tải sau chỉ xếp hàng tới khi restart | `downloader.py`, `modals/base.py` |
| P0-2 | Chặn | Huỷ khi game còn trong hàng chờ không xoá item, tải vẫn chạy sau đó | `downloader.py`, `modals/game_action.py` |
| P1-1 | Nặng | Danh sách báo đã tải theo base name, chi tiết chỉ khớp đúng tên catalogue | `screens/store.py`, `modals/game_action.py` |
| P1-2 | Nặng | Store không truyền đường dẫn bản cài thật cho modal | `screens/store.py` |
| P1-3 | Nặng | `delete_game` xoá theo tên catalogue nên không xoá gì, vẫn báo "Đã xóa"; companion và boxart thật ở lại | `screens/store.py` |
| P1-4 | Vừa | Boxart lưu theo tên ROM đã bung, UI tìm theo tên catalogue | `downloader.py`, `ui/boxart.py` |
| P2-1 | Nặng | Nhánh zip bung thẳng vào `Roms/`, không staging, không kiểm dung lượng | `downloader.py` |
| P2-2 | Vừa | Companion `.cue/.bin` move theo basename nên archive 2 đĩa ghi đè nhau | `archive.py` |
| P3-1 | Vừa | `is_downloading()` so theo title nên game khác hệ trùng tên bị coi là đang tải | `modals/game_action.py` |
| P3-2 | Vừa | `_check_download_transition` tin `dl_state` toàn cục, có thể báo thành công cho game khác | `modals/game_action.py` |
| P3-3 | Vừa | Turbo 4 luồng không kiểm `Content-Range` của phản hồi 206 | `downloader.py` |
| P3-4 | Vừa | `list_entries` trả `(0, [])` khi parse thất bại, guard dung lượng bị bỏ qua im lặng | `archive.py` |
| P3-5 | Vừa | `scan_all_downloaded_games` hardcode `Roms`, bỏ qua casing `Roms/roms/ROMS` | `catalog.py` |
| P3-6 | Nhẹ | Code chết: `d_url` trong REGET, `source_name` không UI nào đọc | `modals/game_action.py`, `downloader.py` |

## 3. Việc đã làm

| Việc | Nội dung | Trạng thái |
|------|----------|------------|
| W1 | `release_result_slot()` + gọi khi đóng modal kết quả | xong |
| W2 | `cancel_download()` xoá item khỏi hàng chờ, thêm key i18n | xong |
| W3-W4 | `rh/installed.py` (module lá) + store truyền đường dẫn bản cài thật | xong |
| W5 | `is_downloaded()` khớp theo base name qua `installed.find` | xong |
| W6 | `delete_game` xoá ROM chính + companion cùng base + boxart, báo đúng thực tế | xong |
| W7 | Boxart: ghi thêm bản sao theo tên catalogue, tra ngược qua bản cài | xong |
| W8 | Nhánh zip bung vào staging, kiểm dung lượng, dọn trong `finally` | xong |
| W9 | Companion chuyển trước, ROM chính sau; rollback nếu lỗi giữa chừng | xong |
| W10 | Giữ cấu trúc thư mục trong archive (thay vì ghi đè basename) | xong |
| W11 | Kiểm `Content-Range` khớp offset trong turbo | xong |
| W12 | `parse_list_output()` phân biệt "không đọc được" với "0 byte" | xong |
| W13 | `scan_all_downloaded_games` dùng `get_roms_root()` + `img_dir` theo state | xong |
| W14 | `is_downloading()`/`_check_download_transition` so theo `game_key` | xong |
| W15 | Dọn code chết, hiển thị tên nguồn đang tải | xong |
| U1 | UI: bỏ nút trong card (thao tác ở footer), bỏ card "tải game ngay" và card gợi ý phím | xong |
| U2 | UI: card thông tin 4 dòng đều lề (có dòng dung lượng), card downloading thẳng lề | xong |
| U3 | UI: mọi chuỗi trong màn chi tiết/store/emu store/theme/icon/utilities qua `tr()` (VI+EN) | xong |
| U4 | UI: header store sau search = `Kết quả tìm kiếm cho "keyword"` | xong |
| U5 | Lỗi: lưới hành động bị vẽ cả khi game chưa tải (tile cao âm, dồn xuống đáy) | xong |

## 4. Kiểm chứng

- `python _src/selftest_download.py` - 22 check headless, offline, chạy trên thẻ
  SD giả (hàng chờ, huỷ, khớp bản cài, xoá, giải nén staging, guard dung lượng,
  `Content-Range`, parse 7zz, casing `roms`, PICO-8).
- `python _src/selftest_ui.py` - render thật bằng SDL (cần `SDL_VIDEODRIVER=dummy`
  + DLL SDL2): modal 3 trạng thái, không vẽ lưới hành động khi chưa tải, header
  search đúng cả VI/EN, không thiếu key i18n.
- `tools/make_release.py` step 1 (syntax), 2 (i18n), 4 (mô phỏng OTA): pass.
- Compile toàn bộ payload OK; quét import chết trên file đã sửa: sạch.

## 5. Chi phí / hiệu năng / tài nguyên

- Thực thi: thêm một lần quét thư mục hệ máy khi mở modal hoặc dựng danh sách
  store (cache TTL 3 giây, xoá cache sau khi tải/xoá); giải nén zip ghi vào
  staging rồi `os.replace` (cùng thẻ, không copy thêm byte); turbo thêm một phép
  so header mỗi lần đọc.
- Hiệu năng: không thêm việc gì trên đường render mỗi frame; tải vẫn 4 luồng;
  kiểm `Content-Range` loại được trường hợp file hỏng rồi phải tải lại.
- Tài nguyên: staging tốn dung lượng tạm đúng bằng phần đã bung (kiểm trước,
  xoá trong `finally`). Payload thêm `rh/installed.py` (~5 KB).

## 6. Hạn chế đã biết

- Game nhiều file (cue/bin) mà archive đặt tên lạ: `.cue` được đổi theo tên kho,
  `.bin` giữ nguyên nên tham chiếu còn đúng. Nếu `.cue`/`.m3u` tham chiếu chính
  tên ROM chính thì không đổi tên; khi đó store vẫn hiện "chưa tải" sau khi
  khởi động lại (trong phiên vừa tải thì đúng).
- Xoá game chỉ xoá companion cùng base, không xoá track đặt tên khác kiểu
  "Game (Track 1).bin".
- Không thêm hộp xác nhận trước khi xoá (giữ hành vi cũ).
- Trên Windows: `storage.free_space` thiếu `os.statvfs` nên bước kiểm dung lượng
  bị bỏ qua kèm cảnh báo, và cập nhật kho game trong app vẫn lỗi trên desktop.

## 7. Còn lại (đợt sau)

- Đa ngôn ngữ cho các màn cũ: `modals/common.py`, `modals/netplay.py`,
  `screens/youtube.py`, `modals/update.py`, `screens/library.py`, `services.py`,
  `sysinfo.py` (phần lớn là chuỗi tiếng Việt cứng, hiện vẫn hiện tiếng Việt khi
  chọn EN).
- Xoá game: companion theo track và hộp xác nhận (nếu muốn).
- Trên máy thật: Wi-Fi yếu, rút mạng giữa tải, hủy giữa tải, thẻ gần đầy,
  PS `.7z` nhiều đĩa, PSP `.rar`, J2ME `.jar`, restart rồi kiểm badge.

## 8. Phát hành

| Đợt | Version đề xuất | Nội dung note |
|-----|-----------------|---------------|
| 1 | 2.37 | Sửa hàng chờ tải, màn chi tiết khớp bản cài, giải nén an toàn, UI đa ngôn ngữ |

Quy trình: bump `files/rh/version.py`, cập nhật `note` trong `manifest.json` +
`_src/build_changelog.py`, commit, tag, push để CI sinh manifest/site và phát
hành OTA (theo `.agents/memory/release-workflow.md`).
