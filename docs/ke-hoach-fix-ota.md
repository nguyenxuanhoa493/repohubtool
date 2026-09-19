# Kế hoạch sửa lỗi OTA: đã lên 2.37 mà vẫn mời cập nhật 2.37

## 1. Hiện tượng người dùng báo

Máy đã cài 2.37, thoát app rồi mở lại vẫn thấy popup cập nhật và tiêu đề ghi
`v2.37 -> v2.37`. Bấm Cài đặt thì tải lại vài file, lần sau mở app vẫn lặp.

## 2. Điều kiện hiện popup (hiện tại)

`files/rh/updater.py:568-570`:

    if (not is_newer(m["version"], APP_VERSION)
            and not catalog_pending(m) and not runtime_pending(m)):
        return None

Popup hiện khi **một trong ba** điều kiện đúng: có bản mới hơn, **kho game lệch**,
hoặc **bộ giả lập (JAVA) lệch**. Modal lại vẽ `v{APP_VERSION} -> v{manifest.version}`
(`modals/update.py`) nên hai nhánh sau bị người dùng đọc thành "cập nhật lên 2.37".

## 3. Nguyên nhân

### N1 - file runtime vừa được phát hành vừa do app ghi

`manifest["runtime"]["files"]` gồm 8 file, trong đó có `default_phone.cfg`,
`config.json`, `zulu17/bin/keymap.cfg`, `launch.sh` (đều nằm trong `Emus/JAVA/`).

`runtime_pending()` (`updater.py:333-350`) băm 8 file này trên máy và so hash.
Màn Cài đặt J2ME (tính năng mới ở 2.37) cho người dùng đổi chế độ điện thoại /
độ phân giải -> ghi lại chính `default_phone.cfg`/`config.json` -> hash lệch vĩnh
viễn -> `runtime_pending()` không bao giờ rỗng -> popup mỗi lần mở app.

### N2 - settings.json nằm trong payload nhưng không bao giờ được ghi đè

`pending_files()` (`updater.py:419-426`) so hash **mọi** file trong
`manifest["files"]`, gồm `settings.json` (manifest 2.37 có: hash `0e1f97d2...`,
267 B). Nhưng `apply_update()` cố ý bỏ qua `settings.json` để giữ cấu hình người
dùng (`updater.py:638-644`), còn app luôn ghi lại `device_id`/`catalog_sha`/
`skipped_versions` -> hash trên máy luôn khác manifest. Vì vậy sau mỗi lần cài,
`pending_files()` vẫn còn ít nhất 1 file, modal lại liệt kê file đó.

### N3 (phụ, cần loại trừ)

`catalog_pending()` so `manifest["catalog"]["sha256_plain"]` với `state.catalog_sha`.
Nếu lần cài catalogue thất bại (mạng yếu) thì `catalog_sha` rỗng -> popup lại. Ở
2.37 hash là `70de070f3bef0b6b...`, khớp DB trong repo, nên chỉ cần một lần cài
thành công là hết - trừ khi bị N1 kéo theo.

## 4. Việc sẽ làm

| # | Việc | File | Tiêu chí |
|---|------|------|----------|
| W1 | Viết test tái hiện trước (TDD): `_src/selftest_ota.py` với các case N1/N2 | mới | test đỏ trên code hiện tại |
| W2 | Bỏ file người dùng khỏi `manifest["runtime"]["files"]` (chỉ giữ file phát hành: NOTICE.txt, launch.sh, zulu17/bin/*) | `manifest.json` + `tools/make_release.py` (ghi rõ danh sách loại trừ) | test N1 xanh |
| W3 | Bỏ `settings.json` khỏi payload: skip khi quét **và** không thêm vào `remove` | `tools/make_release.py` | test N2 xanh |
| W4 | `pending_files()` bỏ qua `settings.json` (phòng khi bản cũ còn trong manifest) | `updater.py` | test N2b xanh |
| W5 | Sau khi cài xong: kiểm lại và ghi log phần còn lệch (tên file + hash) vào `RetroHub-loi.txt` | `modals/update.py` | log có dòng "con lech: ..." |
| W6 | Modal nói đúng bản chất: khi `is_newer()` false thì tiêu đề là "Cập nhật kho game / bộ giả lập", không vẽ `v2.37 -> v2.37`; thêm key i18n VI+EN | `modals/update.py`, `i18n.py` | 2 ngôn ngữ, key đủ |
| W7 | Chống lặp vô hạn: file runtime không khớp sau khi đã cài 1 lần thì coi là "bản người dùng", bỏ khỏi so sánh và cảnh báo | `updater.py` | test N1b |

## 5. Kiểm chứng

- `python _src/selftest_ota.py`: N1 (runtime_pending không kêu khi chính app đổi
  `default_phone.cfg`), N2 (pending_files bỏ qua `settings.json`), N3 (manifest
  runtime không chứa file người dùng), N4 (chuỗi cài - kiểm - cài không lặp).
- `python _src/selftest_download.py` + `python _src/selftest_ui.py` (hồi quy).
- `python tools/make_release.py` step 1/2/4 trên Linux/WSL.
- Máy thật: cài J2ME -> đổi chế độ điện thoại -> thoát/mở app 3 lần, popup không
  được quay lại; kiểm `RetroHub-loi.txt` sau mỗi lần.

## 6. Chi phí / hiệu năng / tài nguyên

- Bỏ 2 file khỏi runtime: mỗi lần cập nhật bớt được ~2 lượt tải nhỏ (vài KB),
  đồng thời hết vòng lặp tải lại 8 file.
- Bỏ `settings.json` khỏi payload: payload nhỏ hơn 267 B, nhưng quan trọng hơn là
  `pending_files()` hội tụ sau 1 lần cài (bớt hẳn việc tải lại mỗi lần mở app).
- W7 thêm 1 vòng so hash 8 file sau khi cài (chỉ chạy trong luồng cập nhật, không
  nằm trên đường render) - không ảnh hưởng FPS/pin.

## 7. Rủi ro

- `manifest["runtime"]` là dữ liệu phát hành; đổi danh sách file phải đi kèm bump
  version (2.38) để máy cũ nhận được thay đổi.
- Nếu máy đang có `default_phone.cfg` do người dùng sửa, sau khi bỏ khỏi manifest
  thì file đó giữ nguyên - đúng mong muốn, nhưng cần ghi chú trong release note.
- Không được để W7 che mất lỗi thật: chỉ bỏ qua file runtime *sau khi* đã cài
  thành công ít nhất một lần và hash chỉ lệch ở file người dùng.

## 8. Phát hành

Bump `files/rh/version.py` -> 2.38, cập nhật `note` (vi+en) trong `manifest.json`,
thêm mục `_src/build_changelog.py`, commit, tag, push; CI sinh manifest/site, purge
jsDelivr và báo Telegram (đã bổ sung ở commit 2a6947d).

## 9. Cần chốt

1. W6: tiêu đề modal khi chỉ lệch kho game/runtime nên là gì (đề xuất: "Cập nhật kho game & bộ giả lập J2ME")?
2. N1: chuyển cấu hình J2ME sang file riêng `Emus/JAVA/user.cfg` (sạch hơn), hay chỉ bỏ 2 file khỏi manifest (nhanh hơn)?
