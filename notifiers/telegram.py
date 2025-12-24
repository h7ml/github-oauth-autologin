"""Telegram 通知器实现"""
import os
import time
import re
import requests
from typing import Optional
from core.types import NotifierInterface


class TelegramNotifier(NotifierInterface):
    """Telegram 通知器"""

    def __init__(self):
        self.token = os.environ.get('TG_BOT_TOKEN')
        self.chat_id = os.environ.get('TG_CHAT_ID')
        self.enabled = bool(self.token and self.chat_id)

    def notify(self, message: str, level: str = "INFO", attachments: list[str] = None):
        """发送通知"""
        if not self.enabled:
            return

        try:
            requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                data={"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"},
                timeout=30
            )
        except Exception:
            pass

    def send_photo(self, path: str, caption: str = ""):
        """发送图片"""
        if not self.enabled or not os.path.exists(path):
            return

        try:
            with open(path, 'rb') as f:
                requests.post(
                    f"https://api.telegram.org/bot{self.token}/sendPhoto",
                    data={"chat_id": self.chat_id, "caption": caption[:1024]},
                    files={"photo": f},
                    timeout=60
                )
        except Exception:
            pass

    def wait_user_input(self, prompt: str, pattern: str, timeout: int = 120) -> Optional[str]:
        """等待用户输入（如验证码）"""
        if not self.enabled:
            return None

        offset = self._flush_updates()
        deadline = time.time() + timeout
        regex = re.compile(pattern)

        self.notify(prompt, "WARN")

        while time.time() < deadline:
            try:
                r = requests.get(
                    f"https://api.telegram.org/bot{self.token}/getUpdates",
                    params={"timeout": 20, "offset": offset},
                    timeout=30
                )
                data = r.json()

                if not data.get("ok"):
                    time.sleep(2)
                    continue

                for upd in data.get("result", []):
                    offset = upd["update_id"] + 1
                    msg = upd.get("message") or {}
                    chat = msg.get("chat") or {}

                    if str(chat.get("id")) != str(self.chat_id):
                        continue

                    text = (msg.get("text") or "").strip()
                    match = regex.match(text)
                    if match:
                        return match.group(1) if match.groups() else text

            except Exception:
                pass

            time.sleep(2)

        return None

    def _flush_updates(self) -> int:
        """刷新更新偏移量"""
        if not self.enabled:
            return 0

        try:
            r = requests.get(
                f"https://api.telegram.org/bot{self.token}/getUpdates",
                params={"timeout": 0},
                timeout=10
            )
            data = r.json()
            if data.get("ok") and data.get("result"):
                return data["result"][-1]["update_id"] + 1
        except Exception:
            pass

        return 0
