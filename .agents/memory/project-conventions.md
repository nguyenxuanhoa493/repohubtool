# Project Conventions

- **Toàn vẹn manifest.json:** Bất cứ khi nào sửa đổi tệp tin trong `files/`, luôn phải tính lại size và mã SHA-256 rồi ghi vào `manifest.json`.
- **Chuỗi đường dẫn SDL2:** `PYSDL2_DLL_PATH` luôn tuân thủ thứ tự: `$APP/libs:/usr/trimui/lib:/usr/lib64:/usr/lib` để tương thích TrimUI Brick, Smart Pro, Smart Pro S (TSPS) và các máy Linux handheld khác.
- **Website build:** Chạy `python3 _src/build_changelog.py && python3 _src/build.py` để đồng bộ website song ngữ sau mỗi lần phát hành.
- **Không dùng icon/emoji trong text nút bấm & tiêu đề UI:** Tuyệt đối không chèn emoji hoặc ký hiệu biểu tượng (như ⚙, ⚡, 🎮,...) vào chuỗi text hiển thị trên nút bấm (button text) hoặc tiêu đề UI. Font TTF trên máy cầm tay thường không có glyph emoji, dễ gây lỗi ô vuông `□` hoặc vỡ layout. Luôn dùng text chữ thuần túy, kèm nhãn phím cứng nếu có (ví dụ: `CÀI ĐẶT JAVA (START)`).
- **Quy tắc thiết kế UI chống đè chữ (Text Overlap Prevention Rules):**
  1. **Ngân sách chiều rộng hai cột (Width Budgeting):** Trong bất kỳ hàng chia 2 cột nào (Label trái - Value phải), không bao giờ để hai bên nở tự do không giới hạn. Luôn gán trần `max_w` cụ thể (ví dụ: Label trái `max_w = 280`, Value phải `max_w = 380`), đảm bảo luôn có khoảng đệm an toàn tối thiểu 20px giữa 2 khối text.
  2. **Tự động cắt an toàn (Auto-Ellipsis với `draw_text(..., max_w=...)` / `draw_text_fit`):** Mọi text động, tên file, giá trị option, hoặc chuỗi dịch i18n phải được giới hạn `max_w`. Hàm đồ họa sẽ tự động cắt tỉa chuỗi và thêm `...` nếu vượt ngưỡng, triệt tiêu khả năng đè chữ.
  3. **Tối giản hóa giá trị trong control (Concise Values + External Hint):** Giá trị trong control (nút toggle, slider, dropdown) chỉ hiển thị từ khóa ngắn gọn (ví dụ: `HQ (Nét cao)`, `Smooth (Mịn)`, `Nokia N (Chuẩn game)`). Toàn bộ nội dung mô tả, giải thích chi tiết phải được đưa xuống dòng chú thích động (Contextual Hint box bên dưới).
  4. **Không nhồi nhét song ngữ kép trong một nhãn:** Tránh viết kiểu `Kiểu hiển thị (Display):` hay `Chế độ máy (Keypad):`. Dùng bộ dịch i18n chuẩn để hiển thị thuần một ngôn ngữ theo ngữ cảnh (`VI` hoặc `EN`).

