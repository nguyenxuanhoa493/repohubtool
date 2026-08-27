# retrohub-update

Kênh phát hành cho RetroHub trên TrimUI Brick.

- `manifest.json` — phiên bản hiện hành và sha256 của từng tệp
- `files/` — nội dung bản phát hành (bytecode `.pyc` + tài nguyên)

Ứng dụng đọc `manifest.json`, so với phiên bản đang cài, rồi chỉ tải những
tệp có sha256 khác. Mỗi tệp được kiểm hash trước khi ghi đè.

Không thêm `.gitignore` kiểu Python vào repo này: mẫu chuẩn có dòng
`*.py[cod]` sẽ loại sạch bản phát hành.
