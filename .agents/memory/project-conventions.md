# Project Conventions

- **Toàn vẹn manifest.json:** Bất cứ khi nào sửa đổi tệp tin trong `files/`, luôn phải tính lại size và mã SHA-256 rồi ghi vào `manifest.json`.
- **Chuỗi đường dẫn SDL2:** `PYSDL2_DLL_PATH` luôn tuân thủ thứ tự: `$APP/libs:/usr/trimui/lib:/usr/lib64:/usr/lib` để tương thích TrimUI Brick, Smart Pro, Smart Pro S (TSPS) và các máy Linux handheld khác.
- **Website build:** Chạy `python3 _src/build_changelog.py && python3 _src/build.py` để đồng bộ website song ngữ sau mỗi lần phát hành.
