"""Module quản lý các secret và API Key được mã hóa obfuscation."""

from .security import decrypt_key

# Chuỗi đã được mã hóa (Không lưu plain-text trong codebase)
_ENC_TELEGRAM_BOT_TOKEN = "_hPXXYV~e7aWSP-(k<;LUHDx$2^XGs&K1EX7wT*Xc^j4~lz+Tb7q2Wz1Y!"
_ENC_AI_API_KEY = ""


def get_telegram_token() -> str:
    """Giải mã Telegram Bot Token trong bộ nhớ RAM khi cần sử dụng."""
    return decrypt_key(_ENC_TELEGRAM_BOT_TOKEN)


def get_ai_key() -> str:
    """Giải mã AI API Key (Gemini, OpenAI, etc.) trong bộ nhớ RAM khi cần sử dụng."""
    return decrypt_key(_ENC_AI_API_KEY)
