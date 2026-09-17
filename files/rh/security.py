import base64

# Salt đa tầng cho phép biến đổi XOR
_SALT = [0x5A, 0x3C, 0x7E, 0x1F, 0x9B, 0x24, 0x6D, 0x88, 0x4F, 0xA2, 0x13, 0xD7]


def _xor_cipher(data: bytes, key: list) -> bytes:
    """Mã hóa / Giải mã XOR đối xứng với chuỗi Salt tuần hoàn."""
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])


def encrypt_key(raw_text: str) -> str:
    """Mã hóa chuỗi plain text thành chuỗi obfuscated Base85 an toàn."""
    if not raw_text:
        return ""
    raw_bytes = raw_text.strip().encode("utf-8")
    # Tầng 1: XOR với Salt
    xored = _xor_cipher(raw_bytes, _SALT)
    # Tầng 2: Đảo ngược chuỗi byte
    reversed_bytes = xored[::-1]
    # Tầng 3: Base85 Encoding
    return base64.b85encode(reversed_bytes).decode("ascii")


def decrypt_key(encrypted_str: str) -> str:
    """Giải mã chuỗi obfuscated thành plain text lúc runtime trong RAM."""
    if not encrypted_str:
        return ""
    try:
        raw_b85 = base64.b85decode(encrypted_str.strip().encode("ascii"))
        unreversed = raw_b85[::-1]
        decrypted = _xor_cipher(unreversed, _SALT)
        return decrypted.decode("utf-8")
    except Exception:
        return ""
