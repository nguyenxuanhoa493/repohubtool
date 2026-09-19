# Quy Trình Đóng Góp & Phát Triển (Contribution & Development Guide)

Dự án RetroHub áp dụng quy trình làm việc chuẩn hóa dựa trên nhánh (feature branch) và Pull Request (PR) để đảm bảo tính ổn định, tránh xung đột mã nguồn và kiểm soát chất lượng bản phát hành.

---

## 🚀 Quy trình các bước chuẩn

### 1. Đồng bộ mã nguồn mới nhất từ nhánh `main`
Luôn kéo mã nguồn mới nhất trước khi bắt đầu công việc:
```bash
git checkout main
git pull origin main
```

### 2. Tạo nhánh làm việc mới
Quy ước đặt tên nhánh: `<user>/<loại>-<nội-dung>`
- `<user>`: Tên hoặc username của bạn (ví dụ: `swpts`, `xuanhoa`, ...)
- `<loại>`: Tiền tố phân loại công việc:
  - `fix`: Sửa lỗi (bug fix)
  - `feat`: Tính năng mới (new feature)
  - `ui`: Chỉnh sửa giao diện, font, layout
  - `refactor`: Tái cấu trúc mã nguồn
  - `docs`: Tài liệu hướng dẫn
- `<nội-dung>`: Mô tả ngắn gọn bằng kebab-case (tiếng Anh)

**Ví dụ:**
```bash
git checkout -b swpts/fix-youtube-ui
```

### 3. Phát triển, commit và mở Pull Request (PR)
1. Thực hiện code và kiểm tra kỹ tại local.
2. Commit và đẩy nhánh lên GitHub:
   ```bash
   git add .
   git commit -m "fix(ui): adjust layout for youtube screen"
   git push -u origin swpts/fix-youtube-ui
   ```
3. Tạo **Pull Request** từ nhánh của bạn vào nhánh `main`.
4. **Quy định Review & An toàn:**
   - **Xử lý xung đột (Conflicts):** Nếu hai người cùng sửa vào một file, GitHub sẽ cảnh báo xung đột ngay tại PR này để giải quyết trước khi vào `main`.
   - **Đánh giá (Code Review):** Cần ít nhất 1 người (bác hoặc em) review và bấm **Approve** trước khi được merge.
   - **Tương lai:** Bổ sung workflow tự động chạy kiểm tra bảo mật (security check), deploy preview và khóa nhánh `main` (branch protection).

### 4. Merge vào nhánh `main`
- Sau khi được approve và giải quyết xong conflict (nếu có), thực hiện Merge PR vào nhánh `main`.

### 5. Cập nhật mã nguồn ở local và Phát hành (Release)
1. Sau khi PR đã merge thành công trên GitHub, quay lại máy local và đồng bộ:
   ```bash
   git checkout main
   git pull origin main
   ```
2. Nếu bản này sẵn sàng phát hành cho người dùng (đã cập nhật version trong `files/rh/version.py`, ghi chú vào `manifest.json` và changelog):
   ```bash
   git tag vX.XX
   git push origin main --tags
   ```
3. GitHub Actions (`release.yml`) sẽ tự động kích hoạt workflow kiểm tra, đóng gói và phát hành bản cập nhật (OTA & Release).
