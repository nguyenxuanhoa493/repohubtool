# Release Workflow Conventions

## ⚠️ QUY TẮC PHÁT HÀNH (MANDATORY RULE)

### 1. Mặc định ("phát hành đi", "phát hành bản mới"): CHỈ PHÁT HÀNH OTA (Bản cập nhật)
Khi người dùng yêu cầu "phát hành", "phát hành đi", "ra bản mới":
- **Mục tiêu:** Cho phép máy cầm tay kết nối Wi-Fi tự nhận và tải các tệp cập nhật mới nhất.
- **Các bước thực hiện:**
  1. Nâng `APP_VERSION` trong `files/rh/version.py`.
  2. Cập nhật `manifest.json`:
     - Nâng `version` tương ứng.
     - Cập nhật ghi chú `note` (vi & en).
     - Tính toán lại dung lượng và mã SHA-256 cho toàn bộ các file đã chỉnh sửa trong `files/`.
     - Giữ nguyên `full_release_version` trỏ tới bản full zip đã phát hành gần nhất để link tải trên website KHÔNG bị 404.
  3. Cập nhật `_src/build_changelog.py` và chạy `python3 _src/build_changelog.py && python3 _src/build.py`.
  4. Git commit và `git push origin main`.
  5. Thử đồng bộ qua SSH sang thiết bị nếu máy đang online.
- **TUYỆT ĐỐI KHÔNG:** Không tự ý nén các file full zip (`RetroHub-*-full.zip`, `NextUI.zip`) và không chạy `gh release create`.

---

### 2. Khi người dùng YÊU CẦU RÕ RÀNG ("phát hành bản full", "đóng gói release zip",...): MỚI PHÁT HÀNH BẢN FULL
- Chỉ kích hoạt quy trình này khi người dùng nói cụ thể:
  - *"phát hành bản full"*
  - *"đóng gói file zip"*
  - *"tạo release trên GitHub"*
- **Các bước thực hiện:**
  1. Cập nhật `full_release_version` trong `manifest.json` lên phiên bản mới.
  2. Đóng gói 4 tệp phát hành (`RetroHub-X.XX-full.zip`, `RetroHub-X.XX-NextUI.zip`, `RetroHub-X.XX.zip`, `RetroHub.pak.zip`).
  3. Chạy `gh release create vX.XX ...` để đẩy các assets lên GitHub Releases.
  4. Chạy lại `python3 _src/build.py` để website cập nhật link tải sang phiên bản mới.
  5. Kiểm tra mã phản hồi HTTP 200 cho các link tải.
