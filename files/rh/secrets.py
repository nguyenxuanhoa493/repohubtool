# -*- coding: utf-8 -*-
"""Module quản lý các secret và API Key được mã hóa hoặc nạp từ môi trường.

Ưu tiên nạp theo thứ tự:
1. Biến môi trường hệ thống (phục vụ CI/CD và môi trường phát triển).
2. File cấu hình bí mật cục bộ (secrets.json trên thẻ nhớ hoặc secrets.local.json).
3. Chuỗi mã hóa obfuscation tùy chỉnh nếu được cấu hình.
"""

import os
import json
from .security import decrypt_key

# Chuỗi mã hóa mặc định rỗng để đảm bảo tuyệt đối không lộ secret thật trong codebase.
_ENC_TELEGRAM_BOT_TOKEN = ""
_ENC_AI_API_KEY = ""

_CACHED_SECRETS = None


def _load_local_secrets() -> dict:
    """Đọc file secrets nội bộ từ thẻ nhớ hoặc thư mục ứng dụng nếu tồn tại."""
    global _CACHED_SECRETS
    if _CACHED_SECRETS is not None:
        return _CACHED_SECRETS

    _CACHED_SECRETS = {}
    try:
        from .paths import SDCARD_PATH, APP_DIR
        sd = os.environ.get("SDCARD_PATH") or SDCARD_PATH
        candidate_paths = [
            os.path.join(sd, "RetroHub", "secrets.json"),
            os.path.join(APP_DIR, "data", "secrets.json"),
            os.path.join(os.path.dirname(__file__), "secrets.local.json"),
        ]
        for p in candidate_paths:
            if os.path.isfile(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            _CACHED_SECRETS.update(data)
                            break
                except Exception:
                    pass
    except Exception:
        pass

    return _CACHED_SECRETS


def get_telegram_token() -> str:
    """Lấy Telegram Bot Token theo thứ tự: Env -> Local file -> Obfuscated string."""
    # 1. Biến môi trường
    env_token = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    if env_token:
        return env_token

    # 2. File cấu hình cục bộ không commit git
    local_token = (_load_local_secrets().get("telegram_bot_token") or "").strip()
    if local_token:
        return local_token

    # 3. Chuỗi obfuscated (nếu có cấu hình riêng)
    if _ENC_TELEGRAM_BOT_TOKEN:
        return decrypt_key(_ENC_TELEGRAM_BOT_TOKEN)

    return ""


def get_ai_key() -> str:
    """Lấy AI API Key theo thứ tự: Env -> Local file -> Obfuscated string."""
    # 1. Biến môi trường
    for env_var in ("AI_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY"):
        val = (os.environ.get(env_var) or "").strip()
        if val:
            return val

    # 2. File cấu hình cục bộ không commit git
    local_key = (_load_local_secrets().get("ai_api_key") or "").strip()
    if local_key:
        return local_key

    # 3. Chuỗi obfuscated (nếu có cấu hình riêng)
    if _ENC_AI_API_KEY:
        return decrypt_key(_ENC_AI_API_KEY)

    return ""
