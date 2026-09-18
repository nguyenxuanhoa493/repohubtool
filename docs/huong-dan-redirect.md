# Hướng dẫn giữ link cũ cho máy chưa cập nhật

## Bối cảnh

Khi dọn repo, ba thư mục `Themes/zips/`, `EmuIcons/zips/`, `emus/` đã được chuyển
khỏi git sang GitHub Releases (release tag `assets`). Máy đã cài bản cũ vẫn gọi
các link này:

- `https://retrohub.xuanhoa493.com/Themes/zips/<tên>.zip`
- `https://retrohub.xuanhoa493.com/EmuIcons/zips/<tên>.zip`
- `https://retrohub.xuanhoa493.com/emus/<TÊN>.tar.gz`

Hiện các link đó trả 404. Máy sẽ **tự cập nhật (OTA)** qua `files/` + `catalog/`
vẫn còn trên `main`, sau đó dùng link Release mới. Chỉ trong lúc chưa cập nhật thì
tải theme/icon/giả lập mới bị lỗi.

Hạ tầng hiện tại: `retrohub.xuanhoa493.com` là CNAME thẳng tới
`nguyenxuanhoa493.github.io` (GitHub Pages), DNS ở tenten.vn, **không có
Cloudflare**. GitHub Pages không hỗ trợ redirect theo đường dẫn.

---

## Cách A — Không cần làm gì (khuyến nghị)

1. Phát hành bản mới để máy tự cập nhật:

   ```
   git tag v2.36 && git push origin main --tags
   ```

2. CI sẽ tự build và tạo Release. Máy mở app sẽ tự cập nhật rồi dùng link mới.
3. Không cần đụng hạ tầng. Nhược điểm: máy nào chưa mở app có thể tải
   theme/icon/giả lập lỗi tạm thời.

---

## Cách B — Redirect triệt để bằng Cloudflare Worker (nâng cao)

Chỉ làm nếu muốn cả máy chưa cập nhật vẫn tải được. Cần đưa DNS của
`xuanhoa493.com` sang Cloudflare (miễn phí).

### B1. Tạo Cloudflare và trỏ DNS

1. Đăng ký tài khoản tại `dash.cloudflare.com`.
2. **Add a site** → nhập `xuanhoa493.com` → chọn gói **Free**.
3. Cloudflare hiện 2 nameserver dạng `xxx.ns.cloudflare.com`. Vào
   **tenten.vn → Quản lý tên miền → DNS/Nameserver**, thay bằng 2 NS đó.
4. Chờ 5–30 phút cho DNS cập nhật.

### B2. Khai báo bản ghi

Trong Cloudflare → **DNS → Records**, thêm (giữ đúng như cũ):

| Type  | Name      | Content                      | Proxy              |
|-------|-----------|------------------------------|--------------------|
| CNAME | `retrohub`| `nguyenxuanhoa493.github.io` | Proxied (mây vàng) |

Vào **SSL/TLS → Overview**, chọn **Full**.

### B3. Tạo Worker

1. Cloudflare → **Workers & Pages → Create → Worker** → đặt tên
   `retrohub-assets-redirect` → **Deploy**.
2. Bấm **Edit code**, xoá hết, dán đoạn sau rồi **Deploy**:

```js
const RELEASE = "https://github.com/nguyenxuanhoa493/repohubtool/releases/download/assets/";

export default {
  fetch(request) {
    const url = new URL(request.url);
    const path = decodeURIComponent(url.pathname);

    // Gói giả lập: tên không có khoảng trắng
    if (path.startsWith("/emus/")) {
      return Response.redirect(RELEASE + encodeURIComponent(path.slice(6)), 301);
    }

    // Theme / Icon: GitHub đổi tên asset (bỏ '&', space -> '.', gộp '..')
    let name = path.replace(/^\/(Themes\/zips|EmuIcons\/zips)\//, "");
    name = name.replace(/&/g, "").replace(/ /g, ".").replace(/\.{2,}/g, ".");
    return Response.redirect(RELEASE + encodeURIComponent(name), 301);
  },
};
```

### B4. Gắn route cho Worker

Trong Worker → **Settings → Triggers → Routes**, thêm 3 route (zone
`xuanhoa493.com`):

```
retrohub.xuanhoa493.com/emus/*
retrohub.xuanhoa493.com/Themes/zips/*
retrohub.xuanhoa493.com/EmuIcons/zips/*
```

Lưu lại.

### B5. Kiểm tra

Chạy các lệnh sau, kỳ vọng trả về **301** rồi tới file thật (200):

```
curl -sI "https://retrohub.xuanhoa493.com/emus/JAVA.tar.gz" | findstr /I "HTTP location"
curl -sI "https://retrohub.xuanhoa493.com/Themes/zips/Animal%20Crossing.zip" | findstr /I "HTTP location"
curl -sI "https://retrohub.xuanhoa493.com/EmuIcons/zips/Burst%20-%20Stock%20OS%20v1.1.0.zip" | findstr /I "HTTP location"
```

Nếu thấy `location: .../releases/download/assets/...` là đúng.

### B6. Rollback

Nếu có sự cố: Cloudflare → **DNS**, chuyển bản ghi `retrohub` về **DNS only**
(mây xám) hoặc đổi NS ở tenten.vn về lại như cũ. Website quay về GitHub Pages
như trước.

---

## Lưu ý

- Không cần thêm file `Themes/zips`, `EmuIcons/zips`, `emus` trở lại repo —
  redirect lấy trực tiếp từ Release `assets`.
- Sau khi lên bản mới, máy sẽ tự dùng link Release, nên Worker chỉ là lớp tương
  thích cho máy cũ.
- Nếu không muốn đổi DNS sang Cloudflare, dùng **Cách A** là đủ.
