# Release Workflow Conventions

## ⚠️ QUY TẮC PHÁT HÀNH (MANDATORY RULE)

Từ nay việc đóng gói và phát hành do **GitHub Actions** làm
(`.github/workflows/release.yml`). Không nén zip bằng tay, không commit
`dist/`, không tự chạy `gh release create` trên máy.

### 0. Bất biến (không được vi phạm)
- `files/rh/version.py` là **nguồn version duy nhất**. Mọi chỗ khác
  (manifest, tag, website) đều suy ra từ đó.
- `dist/`, `Themes/zips/`, `EmuIcons/zips/`, `emus/*.tar.gz` **không bao giờ
  được commit**. Chúng nằm trên GitHub Releases (release tag `assets`).
- Một file bị track > 5 MB sẽ làm CI `guard-large-files` fail.

### 1. Phát hành OTA ("phát hành đi", "phát hành bản mới")
1. Sửa code trong `files/`.
2. Nâng `APP_VERSION` trong `files/rh/version.py` và cập nhật `note` (vi & en)
   trong `manifest.json`.
3. Cập nhật `_src/build_changelog.py` cho phiên bản mới.
4. Commit, rồi tạo tag và push:
   ```
   git tag vX.XX && git push origin main --tags
   ```
5. CI sẽ: kiểm tra syntax + i18n + mô phỏng OTA, tính lại SHA-256 vào
   `manifest.json`, build website, đóng gói 4 zip, tạo GitHub Release, và
   commit manifest/website trở lại nhánh mặc định.
6. Sau khi CI xong: purge CDN jsDelivr cho `manifest.json` và
   `files/rh/version.py`.
7. Gửi thông báo Telegram bằng `_src/notify_ota_telegram.py`.
8. Thử đồng bộ SSH sang thiết bị nếu máy online.

### 2. Phát hành bản full ("phát hành bản full", "đóng gói release zip")
- Chạy workflow `Build & Release` với input `full = true` (hoặc push tag như
  trên). Cờ `--full` sẽ nâng `full_release_version` trong manifest để link tải
  trên website không bị 404.
- Không đóng gói zip thủ công.

### 3. Thêm/sửa theme, icon, gói giả lập (archive lớn)
1. Đặt file nguồn vào `Themes/zips/`, `EmuIcons/zips/`, hoặc `emus/`.
2. Upload lên release `assets`:
   ```
   GITHUB_TOKEN=... python3 _src/publish_assets.py
   ```
3. Đồng bộ URL trong catalog (GitHub đổi tên asset: space → dấu chấm, bỏ `&`):
   ```
   GITHUB_TOKEN=... python3 _src/migrate_assets_urls.py
   ```
4. Commit catalog đã cập nhật. Các file archive vẫn nằm ngoài git.
