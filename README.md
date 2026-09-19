# retrohub-update

Kênh phát hành cho RetroHub trên TrimUI Brick.

- `manifest.json` — phiên bản hiện hành và sha256 của từng tệp
- `files/` — mã nguồn và tài nguyên của ứng dụng (nguồn duy nhất)
- `.github/workflows/release.yml` — CI đóng gói và phát hành

Ứng dụng đọc `manifest.json`, so với phiên bản đang cài, rồi chỉ tải những
tệp có sha256 khác. Mỗi tệp được kiểm hash trước khi ghi đè.

## Phát hành

Changelog nằm ở `changelogs.json`: thêm **một object** vào mảng `releases` (mới
nhất lên đầu) rồi bump `APP_VERSION` trong `files/rh/version.py` cho khớp. Trang
changelog, `manifest.note` và thông báo Telegram đều sinh ra từ object đó, nên
không phải sửa tay `manifest.json`; thiếu object là `make_release.py` fail ngay.

```
git tag v2.39 && git push origin main --tags
```

CI sẽ kiểm tra, tính lại hash, build website, đóng gói 4 zip và tạo GitHub
Release. Không commit `dist/`, archive theme/icon hay `*.tar.gz`: chúng thuộc
GitHub Releases, không thuộc git. File bị track quá 5 MB sẽ làm CI fail.
