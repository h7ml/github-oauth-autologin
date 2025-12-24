"""站点适配器基类"""
import time
from abc import ABC, abstractmethod
from typing import Optional
from core.types import SiteConfig, GitHubCredentials, NotifierInterface
from core.github_auth import GitHubAuthenticator
from core.oauth_handler import OAuthFlowController
from core.cookie_manager import CookieManager


class SiteAdapter(ABC):
    """站点适配器基类"""

    def __init__(
        self,
        config: SiteConfig,
        credentials: GitHubCredentials,
        notifier: NotifierInterface
    ):
        self.config = config
        self.credentials = credentials
        self.notifier = notifier

        self.github_auth = GitHubAuthenticator(notifier)
        self.oauth_handler = OAuthFlowController(notifier)
        self.cookie_manager = CookieManager(notifier)

    def run(self, context, page) -> bool:
        """执行完整登录流程"""
        print(f"\n{'='*50}")
        print(f"🚀 {self.config.name} 自动登录")
        print(f"{'='*50}\n")

        try:
            # 1. 预加载 Cookie
            if self.credentials.session_cookie:
                self._load_session_cookie(context)

            # 2. 访问登录页
            print(f"🔹 步骤1: 访问 {self.config.name}")
            page.goto(self.config.login_url, timeout=60000)
            page.wait_for_load_state('networkidle', timeout=self.config.timeouts.network_idle * 1000)
            time.sleep(2)

            # 检查是否已登录
            if self._check_already_logged_in(page):
                print("✅ 已登录！")
                self._do_post_login(page)
                self._extract_and_save_cookies(context)
                return True

            # 3. 点击 OAuth 按钮
            print("🔹 步骤2: 点击 GitHub 登录")
            if not self.oauth_handler.click_oauth_button(
                page,
                self.config.oauth_button_selectors,
                "GitHub"
            ):
                print("❌ 未找到 OAuth 按钮")
                return False

            time.sleep(3)
            page.wait_for_load_state('networkidle', timeout=self.config.timeouts.network_idle * 1000)

            # 4. GitHub 认证
            print("🔹 步骤3: GitHub 认证")
            url = page.url

            if 'github.com/login' in url or 'github.com/session' in url:
                if not self.github_auth.login(
                    page,
                    self.credentials,
                    self.config.two_factor,
                    self.config.device_verification
                ):
                    print("❌ GitHub 登录失败")
                    return False
            elif 'github.com/login/oauth/authorize' in url:
                print("✅ Cookie 有效")
                self.oauth_handler.handle_authorization(page)

            # 5. 等待回调
            print("🔹 步骤4: 等待回调")
            if not self.oauth_handler.wait_callback(
                page,
                self.config.success_url_patterns,
                self.config.timeouts.oauth_callback
            ):
                print("❌ 回调失败")
                return False

            # 6. 验证登录
            print("🔹 步骤5: 验证登录")
            if not self._check_already_logged_in(page):
                print("❌ 验证失败")
                return False

            # 7. 登录后操作
            self._do_post_login(page)

            # 8. 提取并保存 Cookie
            self._extract_and_save_cookies(context)

            print(f"\n{'='*50}")
            print("✅ 成功！")
            print(f"{'='*50}\n")

            return True

        except Exception as e:
            print(f"❌ 异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _load_session_cookie(self, context):
        """加载 Session Cookie"""
        try:
            context.add_cookies([
                {
                    'name': 'user_session',
                    'value': self.credentials.session_cookie,
                    'domain': 'github.com',
                    'path': '/'
                },
                {
                    'name': 'logged_in',
                    'value': 'yes',
                    'domain': 'github.com',
                    'path': '/'
                }
            ])
            print("✅ 已加载 Session Cookie")
        except Exception:
            print("⚠️ 加载 Cookie 失败")

    def _check_already_logged_in(self, page) -> bool:
        """检查是否已登录"""
        for pattern in self.config.success_url_patterns:
            if pattern.startswith('!'):
                # 反向匹配
                if pattern[1:] in page.url:
                    return False
            else:
                # 正向匹配
                if pattern not in page.url:
                    return False
        return True

    def _do_post_login(self, page):
        """登录后操作"""
        if not self.config.keepalive_urls:
            return

        print("🔹 步骤6: 保活")
        for keepalive in self.config.keepalive_urls:
            try:
                full_url = keepalive.url
                if not full_url.startswith('http'):
                    # 相对 URL，需要拼接基础 URL
                    base_url = self.config.login_url.rsplit('/', 1)[0]
                    full_url = f"{base_url}{keepalive.url}"

                page.goto(full_url, timeout=30000)
                page.wait_for_load_state('networkidle', timeout=15000)
                print(f"✅ 已访问: {keepalive.name}")
                time.sleep(2)
            except Exception:
                pass

    def _extract_and_save_cookies(self, context):
        """提取并保存 Cookie"""
        print("🔹 步骤7: 更新 Cookie")

        for cookie_name in self.config.cookie_names:
            value = self.cookie_manager.extract_session(
                context,
                self.config.cookie_domain,
                cookie_name
            )

            if value:
                print(f"✅ 提取 Cookie: {cookie_name}")
                self.cookie_manager.save_cookies(value, self.config.cookie_targets)
            else:
                print(f"⚠️ 未获取到 {cookie_name}")
