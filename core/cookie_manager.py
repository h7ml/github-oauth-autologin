"""Cookie 管理器"""
import os
import json
import base64
import logging
from typing import Optional
import requests
from requests.exceptions import RequestException

from core.types import CookieTarget, NotifierInterface
from core.constants import Timeouts, CookieConfig
from utils.retry import retry_network
from utils.security import mask_sensitive

logger = logging.getLogger(__name__)


class CookieManager:
    """Cookie 管理器"""

    def __init__(self, notifier: Optional[NotifierInterface] = None):
        self.notifier = notifier

    def extract_session(
        self,
        context,
        domain: str = CookieConfig.GITHUB_DOMAIN,
        name: str = CookieConfig.SESSION_COOKIE_NAME
    ) -> Optional[str]:
        """提取 Session Cookie
        
        Args:
            context: Playwright BrowserContext
            domain: Cookie 域名
            name: Cookie 名称
            
        Returns:
            Cookie 值，未找到返回 None
        """
        try:
            for cookie in context.cookies():
                if cookie['name'] == name and domain.lstrip('.') in cookie.get('domain', ''):
                    value = cookie['value']
                    logger.info(f"提取 Cookie: {name} = {mask_sensitive(value)}")
                    return value
        except Exception as e:
            logger.error(f"提取 Cookie 失败: {e}")
        return None

    def save_cookies(self, value: str, targets: list[CookieTarget]):
        """保存 Cookie 到多个目标"""
        if not value:
            return

        for target in targets:
            if target.type == "github_secret":
                self._save_to_github_secret(value, target.secret_name)
            elif target.type == "file":
                self._save_to_file(value, target.path, target.encrypt)
            elif target.type == "env":
                self._save_to_env(value, target.secret_name)

    @retry_network(max_attempts=3, delay=2.0)
    def _save_to_github_secret(self, value: str, secret_name: str) -> None:
        """更新 GitHub Actions Secret
        
        Args:
            value: Cookie 值
            secret_name: Secret 名称
        """
        token = os.environ.get('REPO_TOKEN')
        repo = os.environ.get('GITHUB_REPOSITORY')

        if not (token and repo):
            logger.warning("缺少 REPO_TOKEN 或 GITHUB_REPOSITORY，无法自动更新 Secret")
            if self.notifier:
                self.notifier.notify(f"""🔑 <b>新 Cookie</b>

请手动更新 Secret <b>{secret_name}</b>:
<code>{mask_sensitive(value, 6)}</code>""", "WARN")
            return

        try:
            from nacl import encoding, public

            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }

            # 获取公钥
            r = requests.get(
                f"https://api.github.com/repos/{repo}/actions/secrets/public-key",
                headers=headers,
                timeout=Timeouts.API_REQUEST
            )
            r.raise_for_status()

            key_data = r.json()
            pk = public.PublicKey(key_data['key'].encode(), encoding.Base64Encoder())
            encrypted = public.SealedBox(pk).encrypt(value.encode())

            # 更新 Secret
            r = requests.put(
                f"https://api.github.com/repos/{repo}/actions/secrets/{secret_name}",
                headers=headers,
                json={
                    "encrypted_value": base64.b64encode(encrypted).decode(),
                    "key_id": key_data['key_id']
                },
                timeout=Timeouts.API_REQUEST
            )
            r.raise_for_status()

            logger.info(f"✅ 已更新 GitHub Secret: {secret_name}")
            if self.notifier:
                self.notifier.notify(
                    f"🔑 <b>Cookie 已更新</b>\n\n{secret_name} 已保存",
                    "SUCCESS"
                )

        except ImportError:
            logger.error("缺少 pynacl 库，无法加密 Secret")
            if self.notifier:
                self.notifier.notify("❌ 缺少 pynacl 库", "ERROR")
        except RequestException as e:
            logger.error(f"更新 GitHub Secret 失败: {e}")
            if self.notifier:
                self.notifier.notify(f"❌ 更新 {secret_name} 失败: {e}", "ERROR")
            raise

    def _save_to_file(self, value: str, path: str, encrypt: bool = False):
        """保存到文件"""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            data = {"cookie": value}

            with open(path, 'w') as f:
                json.dump(data, f)

            if self.notifier:
                self.notifier.notify(f"💾 Cookie 已保存到 {path}", "SUCCESS")

        except Exception as e:
            if self.notifier:
                self.notifier.notify(f"❌ 保存失败: {str(e)}", "ERROR")

    def _save_to_env(self, value: str, env_name: str):
        """保存到环境变量（仅提示）"""
        if self.notifier:
            self.notifier.notify(f"""🔑 <b>新 Cookie</b>

请设置环境变量 <b>{env_name}</b>:
<code>{value}</code>""", "WARN")
