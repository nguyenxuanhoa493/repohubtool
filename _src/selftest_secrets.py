#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Selftest cho module rh.secrets: Đảm bảo nạp secrets an toàn, hỗ trợ env var và fallback."""

import os
import sys
import tempfile
import json
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "files"))


class TestSecrets(unittest.TestCase):
    def setUp(self):
        # Lưu trữ biến môi trường hiện tại
        self._orig_tele = os.environ.get("TELEGRAM_BOT_TOKEN")
        self._orig_ai = os.environ.get("AI_API_KEY")
        self._orig_gemini = os.environ.get("GEMINI_API_KEY")

    def tearDown(self):
        # Phục hồi biến môi trường
        if self._orig_tele is not None:
            os.environ["TELEGRAM_BOT_TOKEN"] = self._orig_tele
        else:
            os.environ.pop("TELEGRAM_BOT_TOKEN", None)

        if self._orig_ai is not None:
            os.environ["AI_API_KEY"] = self._orig_ai
        else:
            os.environ.pop("AI_API_KEY", None)

        if self._orig_gemini is not None:
            os.environ["GEMINI_API_KEY"] = self._orig_gemini
        else:
            os.environ.pop("GEMINI_API_KEY", None)

    def test_no_hardcoded_plain_secret_in_codebase(self):
        """Đảm bảo không còn chuỗi token thật bị lộ trong secrets.py."""
        from rh import secrets
        self.assertEqual(secrets._ENC_TELEGRAM_BOT_TOKEN, "", "Token Telegram mặc định phải là rỗng!")
        self.assertEqual(secrets._ENC_AI_API_KEY, "", "API key AI mặc định phải là rỗng!")

    def test_read_telegram_token_from_env(self):
        """Ưu tiên đọc Telegram Bot Token từ biến môi trường."""
        from rh import secrets
        os.environ["TELEGRAM_BOT_TOKEN"] = "test_env_token_12345"
        token = secrets.get_telegram_token()
        self.assertEqual(token, "test_env_token_12345")

    def test_read_ai_key_from_env(self):
        """Ưu tiên đọc AI Key từ biến môi trường AI_API_KEY hoặc GEMINI_API_KEY."""
        from rh import secrets
        os.environ.pop("AI_API_KEY", None)
        os.environ["GEMINI_API_KEY"] = "gemini_secret_key_abc"
        key = secrets.get_ai_key()
        self.assertEqual(key, "gemini_secret_key_abc")

        os.environ["AI_API_KEY"] = "primary_ai_key_xyz"
        key = secrets.get_ai_key()
        self.assertEqual(key, "primary_ai_key_xyz")

    def test_read_from_local_json(self):
        """Đọc secret từ file secrets.json khi không có env var."""
        from rh import secrets
        import tempfile
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        secrets._CACHED_SECRETS = None

        with tempfile.TemporaryDirectory() as tmpdir:
            rh_dir = os.path.join(tmpdir, "RetroHub")
            os.makedirs(rh_dir, exist_ok=True)
            sec_file = os.path.join(rh_dir, "secrets.json")
            with open(sec_file, "w", encoding="utf-8") as f:
                json.dump({"telegram_bot_token": "token_from_json_file", "ai_api_key": "ai_from_json_file"}, f)

            orig_sd = os.environ.get("SDCARD_PATH")
            try:
                os.environ["SDCARD_PATH"] = tmpdir
                # Reset cache
                secrets._CACHED_SECRETS = None
                self.assertEqual(secrets.get_telegram_token(), "token_from_json_file")
                self.assertEqual(secrets.get_ai_key(), "ai_from_json_file")
            finally:
                if orig_sd is not None:
                    os.environ["SDCARD_PATH"] = orig_sd
                else:
                    os.environ.pop("SDCARD_PATH", None)
                secrets._CACHED_SECRETS = None


if __name__ == "__main__":
    unittest.main()

