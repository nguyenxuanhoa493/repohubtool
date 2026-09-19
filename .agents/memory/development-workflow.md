# Quy Trình Phát Triển (Development Workflow)

Tài liệu chuẩn hóa quy trình làm việc theo nhánh (branching & PR workflow) cho các cộng tác viên / lập trình viên dự án RetroHub.

---

## 1. Các bước thực hiện chi tiết

### Bước 1: Đồng bộ mã nguồn mới nhất từ `main`
Trước khi bắt đầu bất kỳ tính năng hoặc sửa lỗi nào, luôn đảm bảo nhánh `main` ở local là mới nhất:
```bash
git checkout main
git pull origin main
```

### Bước 2: Tạo nhánh làm việc mới
Tạo nhánh mới từ `main` theo quy ước đặt tên:
- **Cú pháp:** `<user>/<loại>-<nội-dung>`
- **Quy ước:**
  - `<user>`: Tên/username của người làm (ví dụ: `swpts`, `xuanhoa`, ...)
  - `<loại>`: `fix` (sửa lỗi), `feat` (tính năng mới), `refactor`, `docs`, `ui`
  - `<nội-dung>`: Mô tả ngắn gọn bằng tiếng Anh / kebab-case
- **Ví dụ:** `swpts/fix-youtube-ui`, `xuanhoa/feat-cloud-sync`

```bash
git checkout -b swpts/fix-youtube-ui
```

### Bước 3: Code, commit và tạo Pull Request (PR)
1. Thực hiện chỉnh sửa mã nguồn, kiểm tra kỹ lưỡng tại local.
2. Commit và đẩy nhánh lên remote repository:
   ```bash
   git add .
   git commit -m "fix(ui): describe what was changed"
   git push -u origin swpts/fix-youtube-ui
   ```
3. Truy cập GitHub và tạo **Pull Request (PR)** trỏ vào nhánh `main`.
4. **Lợi ích & Quy tắc review:**
   - **Chống đè code (Conflict Resolution):** Mọi xung đột code sẽ được phát hiện và xử lý ngay trên PR trước khi hòa vào nhánh chính.
   - **Review & Approval:** Yêu cầu ít nhất 1 thành viên (ví dụ: bác hoặc em) review và bấm **Approve** trước khi merge.
   - **Định hướng tự động hóa (CI/CD tương lai):**
     - Workflow quét kiểm tra bảo mật (Security check / Linting).
     - Deploy preview (nếu có web/tài liệu).
     - Branch protection rules trên `main`.

### Bước 4: Merge PR vào `main`
- Sau khi được approve và vượt qua các bài kiểm tra, thực hiện Merge PR vào nhánh `main` (trên giao diện GitHub).

### Bước 5: Kéo code mới về local và Kích hoạt Release
1. Quay lại máy local, chuyển về nhánh `main` và kéo commit vừa merge về:
   ```bash
   git checkout main
   git pull origin main
   ```
2. Khi đã sẵn sàng xuất xưởng (lưu ý đã nâng `files/rh/version.py`, `manifest.json` và changelog nếu có):
   ```bash
   git tag vX.XX
   git push origin main --tags
   ```
3. GitHub Actions (`.github/workflows/release.yml`) sẽ tự động kích hoạt quy trình build & release.
