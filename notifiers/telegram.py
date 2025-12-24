"""Telegram 通知器实现"""
import os
import time
import re
import logging
from typing import Optional, List
import requests
from requests.exceptions import RequestException

from core.types import NotifierInterface
from core.constants import Timeouts
from utils.retry import retry_network

logger = logging.getLogger(__name__)


class TelegramNotifier(NotifierInterface):
    """Telegram 通知器"""

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        """初始化 Telegram 通知器

        Args:
            token: Bot Token（可选，默认从环境变量读取）
            chat_id: Chat ID（可选，默认从环境变量读取）
        """
        self.token = token or os.environ.get("TG_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TG_CHAT_ID")
        self.enabled = bool(self.token and self.chat_id)

        if not self.enabled:
            logger.info("Telegram 通知未启用（缺少 Token 或 Chat ID）")

    @retry_network(max_attempts=3, delay=2.0)
    def notify(
        self, message: str, level: str = "INFO", attachments: Optional[List[str]] = None
    ) -> None:
        """发送通知

        Args:
            message: 消息内容
            level: 日志级别
            attachments: 附件列表（暂未使用）
        """
        if not self.enabled:
            return

        try:
            response = requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                data={"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"},
                timeout=Timeouts.API_REQUEST,
            )
            response.raise_for_status()
            logger.debug(f"Telegram 通知发送成功: {message[:50]}...")
        except RequestException as e:
            logger.error(f"Telegram 通知发送失败: {e}")
            raise

    @retry_network(max_attempts=3, delay=2.0)
    def send_photo(self, path: str, caption: str = "") -> None:
        """发送图片

        Args:
            path: 图片文件路径
            caption: 图片说明
        """
        if not self.enabled:
            return

        if not os.path.exists(path):
            logger.warning(f"图片文件不存在: {path}")
            return

        try:
            with open(path, "rb") as f:
                response = requests.post(
                    f"https://api.telegram.org/bot{self.token}/sendPhoto",
                    data={"chat_id": self.chat_id, "caption": caption[:1024]},
                    files={"photo": f},
                    timeout=60,
                )
                response.raise_for_status()
                logger.debug(f"图片发送成功: {path}")
        except RequestException as e:
            logger.error(f"图片发送失败: {e}")
            raise

    def wait_user_input(self, prompt: str, pattern: str, timeout: int = 120) -> Optional[str]:
        """等待用户输入（如验证码）

        Args:
            prompt: 提示消息
            pattern: 匹配正则表达式
            timeout: 超时时间（秒）

        Returns:
            匹配到的输入，超时返回 None
        """
        if not self.enabled:
            logger.warning("Telegram 未启用，无法等待用户输入")
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
                    timeout=30,
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
                        user_input = match.group(1) if match.groups() else text
                        logger.info("收到用户输入")
                        return user_input

            except RequestException as e:
                logger.warning(f"获取 Telegram 更新失败: {e}")
                time.sleep(2)

            time.sleep(2)

        logger.warning("等待用户输入超时")
        return None

    def _flush_updates(self) -> int:
        """刷新更新偏移量，清除旧消息

        Returns:
            新的偏移量
        """
        if not self.enabled:
            return 0

        try:
            r = requests.get(
                f"https://api.telegram.org/bot{self.token}/getUpdates",
                params={"timeout": 0},
                timeout=10,
            )
            data = r.json()
            if data.get("ok") and data.get("result"):
                offset = data["result"][-1]["update_id"] + 1
                logger.debug(f"刷新 Telegram 更新偏移量: {offset}")
                return offset
        except RequestException as e:
            logger.warning(f"刷新 Telegram 更新失败: {e}")

        return 0
