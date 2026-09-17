#!/usr/bin/env python3
"""Script CLI tiện ích dùng để mã hóa API Key / Token trước khi gắn vào codebase."""

import sys
import os

# Thêm đường dẫn files để import rh.security
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "files"))

from rh.security import encrypt_key, decrypt_key


def main():
    if len(sys.argv) > 1:
        raw_key = sys.argv[1].strip()
    else:
        raw_key = input("Nhập Key / Token cần mã hóa: ").strip()

    if not raw_key:
        print("Lỗi: Key không được để trống!")
        return

    encrypted = encrypt_key(raw_key)
    decrypted = decrypt_key(encrypted)

    print("\n" + "=" * 50)
    print("✅ MÃ HÓA THÀNH CÔNG!")
    print(f"Key gốc:      {raw_key[:6]}...{raw_key[-4:] if len(raw_key) > 10 else ''}")
    print(f"Chuỗi mã hóa: {encrypted}")
    print("=" * 50)
    print("\n👉 Hãy sao chép chuỗi mã hóa trên và gán vào `files/rh/secrets.py`.")


if __name__ == "__main__":
    main()
