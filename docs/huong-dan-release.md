# Hướng dẫn phát hành RetroHub

Tóm tắt: **thêm 1 object vào `changelogs.json` + bump `files/rh/version.py` + tag**.
CI lo phần còn lại (hash, site, zip, release, purge cache, Telegram).

---

## 1. Chuẩn bị (2 chỗ, không sửa tay `manifest.json`)

**a. Thêm object vào `changelogs.json`** (mảng `releases`, bản mới nhất lên đầu):

```json
{
  "version": "2.40",
  "date": "2026-09-20",
  "headline": { "vi": "một câu cho popup OTA", "en": "one line for the OTA popup" },
  "bullets": [
    { "vi": "mô tả thay đổi 1", "en": "change 1" },
    { "vi": "mô tả thay đổi 2", "en": "change 2" }
  ]
}
```

File này là **nguồn duy nhất**: trang changelog, `manifest.note` (popup OTA) và thông báo
Telegram đều sinh ra từ đây.

**b. Bump `APP_VERSION` trong `files/rh/version.py`** cho khớp `version` ở trên.

## 2. Kiểm trước khi tag

```bash
python _src/selftest_changelog.py      # JSON + manifest.note + độ dài tin Telegram
python _src/selftest_download.py       # luồng tải / giải nén
python _src/selftest_ota.py            # OTA (J2ME, settings.json)
python _src/selftest_boxart.py         # timeout ảnh bìa
python _src/selftest_ui.py             # render UI (cần SDL2)
python tools/make_release.py --full    # chạy thử toàn bộ pipeline ở local
```

Lưu ý: `make_release.py` **từ chối hash** nếu còn file trong `files/` chưa commit — commit
payload trước khi chạy, hoặc xem cảnh báo "khac voi ban da commit".

## 3. Tag và push

```bash
git tag v2.40
git push origin main --tags
```

## 4. CI (`release.yml`) tự làm gì

1. Kiểm tra tag khớp `files/rh/version.py` (lệch là fail ngay).
2. `make_release.py --publish --full`: syntax, khoá i18n, hash 442 file vào manifest,
   mô phỏng OTA trên 13 bản legacy (v1.20–v2.33), đóng gói 4 zip, build site.
3. Commit `manifest.json` + `index.html` + `vi/changelog` trở lại nhánh `main`.
4. Purge cache jsDelivr cho `manifest.json` và `files/rh/version.py`.
5. Gửi Telegram (nội dung lấy từ `changelogs.json`, tự cắt nếu quá 4096 ký tự).

## 5. Khi có sự cố

| Hiện tượng | Xử lý |
|---|---|
| CI fail "tag does not match APP_VERSION" | Sửa `version.py` hoặc xoá tag rồi tag lại: `git push --delete origin v2.40 && git tag -d v2.40` |
| Fail "changelogs.json chua co muc cho vX" | Thêm object vào `changelogs.json`, commit, tag lại |
| Fail "1 tep trong files/ khac voi ban da commit" | Commit file payload đó rồi chạy lại |
| Telegram không tới (bước này `continue-on-error`) | Gửi tay: `python _src/notify_ota_telegram.py` |
| Máy không thấy bản mới | jsDelivr giữ manifest tới 12 giờ: `curl https://purge.jsdelivr.net/gh/nguyenxuanhoa493/repohubtool@main/manifest.json` |

## 6. Checklist nhanh

- [ ] `changelogs.json` có object mới, đủ `headline` + ít nhất 1 `bullet` (vi và en)
- [ ] `files/rh/version.py` khớp số version
- [ ] Đã commit hết thay đổi trong `files/`
- [ ] `python _src/selftest_changelog.py` pass
- [ ] `python tools/make_release.py --full` pass
- [ ] Tag `vX.XX` đã push; theo dõi tab Actions
