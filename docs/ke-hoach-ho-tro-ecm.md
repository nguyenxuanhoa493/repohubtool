# Kế hoạch: hỗ trợ release nén ECM/APE (đợt sau, KHÔNG làm trong đợt fix bug)

Trạng thái: **chưa làm** — ghi lại để đợt sau xử lý. Đợt hiện tại chỉ fix bug, đã dừng ở
bước báo lỗi đúng bản chất (xem `docs/ke-hoach-fix-tai-game.md`, commit `3333d40`).

## 1. Vấn đề

Nhiều bản PS1 trên nguồn phát hành là "scene rip" nén nhiều tầng, RetroHub không đưa
thẳng cho RetroArch được:

| Lớp | Nội dung | RetroHub hiện tại |
|---|---|---|
| `.rar` | vỏ ngoài, chứa track nhạc + 1 file `.7z` | bung được (7zzs) |
| `.7z` | chứa `*.bin.ecm` (ảnh CD nén ECM) | bung được, nhưng ra file `.ecm` |
| `.bin.ecm` | ảnh CD thô đã bỏ EDC/ECC | **chưa giải mã được** |
| `*.ape` | 19 track nhạc Monkey's Audio | **chưa giải mã được** |
| `.cue` | **không có trong release** | **chưa tự sinh** |

Ví dụ đo thật: `Tomb Raider (E) [SLES-00024]` — 269.037.029 byte (server cũng báo đúng
269.037.029) ⇒ file tải nguyên vẹn; bên trong là 111.032 sector Mode 2 Form 1 + 222.065
record ECM, giải mã ra **293.430.816 byte `bin` 2352 byte/sector**.

## 2. Số đo hiệu năng (làm cơ sở chọn hướng)

Prototype giải mã ECM đúng ngữ nghĩa `unecm` (EDC CRC32 poly `0xD8018001`, ECC Reed-Solomon
trên GF(2^8) với bảng `ecc_f/ecc_b`), chạy trên chính file thật ở trên:

- Python thuần: **0,8 ms/sector** → 111.032 sector ≈ **1,5 phút trên PC x86**, ước **5–8 phút
  trên Brick (Cortex-A53)**. Không dùng được trong luồng tải game (khoá UI, tốn pin).
- C native (kiểu `ecm2bin`): cùng khối lượng ~710M phép tra bảng → ước **1–3s CPU**, thực tế
  bị chặn ở ghi thẻ (293MB) → **~20–40s cho một track**. RAM gần như không tăng, binary
  static aarch64 ~100–200KB.

⇒ Nếu làm, phải là binary native, không phải Python.

## 3. Phương án

- **A. Chỉ ECM (khuyến nghị nếu làm)**: ship `bin/ecm2bin` native; giải mã `.ecm` → `.bin`
  2352 byte/sector. Cứu được các bản chỉ nén ECM (không có track nhạc rời).
- **B. Không làm, giữ nguyên thông báo** (hiện tại): `dl_err_ecm_rom` + khuyên chọn nguồn
  khác. Rẻ nhất, đúng cho release kiểu Tomb Raider ở trên.
- **C. Làm trọn gói ECM + APE→WAV + tự sinh `.cue`**: chỉ khi muốn chơi đúng cả nhạc CD.
  Khối lượng lớn: Monkey's Audio decoder không có bản Python thuần dùng được, và phải suy ra
  cue từ tên track + sector address trong header của image.

Thứ tự nếu triển khai: **A trước**, C để riêng (mở rộng sau, cùng hạ tầng gọi binary).

## 4. Thiết kế nếu chọn A

1. `files/bin/ecm2bin` — binary static aarch64, viết mới (KHÔNG dùng mã GPL của Neill Corlett;
   format ECM + EDC/ECC theo tài liệu công khai ECMA-130). API: `ecm2bin <in.ecm> <out.bin>`,
   thoát 0/khác 0, in tiến trình ra stdout để UI đọc như `7zzs`.
2. `files/rh/ecm.py`: dò binary (giống `archive.sevenzip()`), chạy trong thread nền, cập nhật
   `dl_state["progress_pct"]`/`msg` (i18n VI+EN), huỷ được, xoá file `.ecm` sau khi xong nếu
   `settings.json` cho phép (mặc định xoá để tiết kiệm thẻ).
3. `files/rh/archive.py`: sau `extract_to`, nếu tầng chỉ còn `*.ecm` có magic `ECM` thì gọi
   `ecm.decoder()` rồi quay lại `pick_primary_rom` (không đổi `MAX_DEPTH`, không thêm tầng).
4. Kiểm tra dung lượng trước khi giải mã: file ra lớn hơn file vào ~12% + 64MB margin, dùng
   lại `storage.free_space`.
5. `manifest.json`: thêm `runtime.files` cho binary (đã có cơ chế cho 7zzs/yt-dlp), cập nhật
   `remove` nếu sau này đổi tên.

## 5. Kiểm thử (bắt buộc trước khi ship)

- `_src/selftest_ecm.py`: sinh fixture ECM bằng encoder Python trong test (chỉ cần ghi record
  type 0/1/2 + terminator) từ vài sector thô tự dựng, rồi:
  - giải mã ra đúng byte gốc (so từng sector);
  - **EDC toàn ảnh ở cuối file ECM phải khớp** — đây là phép kiểm tính đúng mạnh nhất, không
    cần oracle ngoài;
  - sai magic / thiếu byte / quá dung lượng → lỗi rõ ràng, không ghi rác vào `Roms/`.
- Đối chiếu một lần với `unecm` gốc build tạm trên PC (chỉ dùng làm oracle khi phát triển,
  không ship) để chốt ECC.
- Test trên máy thật: đo thời gian giải mã 1 track, kiểm tra pin/nhiệt, huỷ giữa chừng.

## 6. Điều kiện tiên quyết / rủi ro

- **Toolchain**: máy build hiện không có gcc/cross-compiler; WSL Ubuntu không có `sudo` phi
  mật khẩu; tải `zig` từ CDN rất chậm. Cần một trong: mật khẩu sudo WSL, Docker Desktop, hoặc
  toolchain aarch64 sẵn có. Không có thì không build được binary ⇒ chọn B.
- **Giấy phép**: nếu ship binary viết tay từ spec công khai thì không vướng GPL; nếu lấy
  `unecm.c` (GPLv2) thì phải kèm source + license trong payload và ghi vào `NOTICE.txt`.
- **Dung lượng**: mỗi track giải mã tốn thêm ~12% thẻ; release như Tomb Raider (1 data track
  + 19 track .ape) sẽ còn cần thêm bước APE nếu muốn có nhạc.
- **UI**: giải mã lâu nên phải chạy nền + có tiến trình, không chặn màn hình tải.
