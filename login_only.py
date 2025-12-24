#!/usr/bin/env python3
"""
GitHub OAuth 自动登录 - 仅登录模式
只负责登录 GitHub（含 2FA），输出 Session Cookie 供其他流程使用
"""
import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright

from core.github_auth import GitHubAuthenticator
from core.types import GitHubCredentials, TwoFactorConfig, DeviceVerificationConfig
from notifiers.telegram import TelegramNotifier


def load_credentials() -> GitHubCredentials:
    """从环境变量加载凭据"""
    username = os.getenv("GH_USERNAME")
    password = os.getenv("GH_PASSWORD")
    session_cookie = os.getenv("GH_SESSION")

    if not username or not password:
        print("❌ 缺少必需的环境变量: GH_USERNAME, GH_PASSWORD")
        sys.exit(1)

    return GitHubCredentials(
        username=username,
        password=password,
        session_cookie=session_cookie
    )


def setup_notifier() -> TelegramNotifier | None:
    """配置 Telegram 通知器"""
    token = os.getenv("TG_BOT_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")

    if token and chat_id:
        return TelegramNotifier(token, chat_id)
    return None


def output_to_github_actions(session_cookie: str, status: str):
    """输出到 GitHub Actions"""
    github_output = os.getenv('GITHUB_OUTPUT')
    if github_output:
        with open(github_output, 'a', encoding='utf-8') as f:
            f.write(f"session={session_cookie}\n")
            f.write(f"status={status}\n")

    # 兼容旧版 GitHub Actions
    print(f"::set-output name=session::{session_cookie}")
    print(f"::set-output name=status::{status}")


def main():
    print("=" * 60)
    print("GitHub OAuth Auto Login - 仅登录模式")
    print("=" * 60)

    credentials = load_credentials()
    notifier = setup_notifier()

    if notifier:
        print("✅ Telegram 通知已启用")
    else:
        print("⚠️  未配置 Telegram（2FA 需要手动处理）")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # 预加载已有 Cookie
            if credentials.session_cookie:
                print("🍪 使用已有 Session Cookie 快速登录")
                context.add_cookies([{
                    'name': 'user_session',
                    'value': credentials.session_cookie,
                    'domain': '.github.com',
                    'path': '/',
                    'secure': True,
                    'httpOnly': True
                }])

            # 访问 GitHub 登录页
            print("🌐 访问 GitHub 登录页...")
            page.goto("https://github.com/login", wait_until="domcontentloaded")

            # 检查是否已登录
            try:
                page.wait_for_selector('[data-login]', timeout=5000)
                print("✅ 已登录 GitHub")
                is_logged_in = True
            except:
                print("🔐 需要执行登录流程")
                is_logged_in = False

            # 执行登录
            if not is_logged_in:
                authenticator = GitHubAuthenticator(notifier)

                two_factor_config = TwoFactorConfig(
                    strategy="auto",
                    mobile_wait=120,
                    totp_wait=120
                )

                device_config = DeviceVerificationConfig(wait=30)

                success = authenticator.login(
                    page, credentials,
                    two_factor_config, device_config
                )

                if not success:
                    print("❌ 登录失败")
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = f"login_failed_{timestamp}.png"
                    page.screenshot(path=screenshot_path, full_page=True)
                    print(f"📸 失败截图: {screenshot_path}")

                    output_to_github_actions("", "failed")
                    browser.close()
                    sys.exit(1)

            # 提取 Session Cookie
            print("🍪 提取 Session Cookie...")
            cookies = context.cookies()
            session_cookie = next(
                (c['value'] for c in cookies
                 if c['name'] == 'user_session' and 'github.com' in c['domain']),
                None
            )

            if not session_cookie:
                print("❌ 未找到 GitHub Session Cookie")
                output_to_github_actions("", "failed")
                browser.close()
                sys.exit(1)

            # 输出结果
            print("=" * 60)
            print("✅ GitHub 登录成功")
            print(f"🍪 Session Cookie: {session_cookie[:20]}...")
            print("=" * 60)

            output_to_github_actions(session_cookie, "success")

            # 自动更新 GitHub Secret（持久化）
            if os.getenv("REPO_TOKEN") and os.getenv("GITHUB_REPOSITORY"):
                try:
                    from core.cookie_manager import CookieManager
                    from core.types import CookieTarget

                    cookie_manager = CookieManager(notifier)
                    cookie_manager.save_cookies(
                        session_cookie,
                        [CookieTarget(type="github_secret", secret_name="GH_SESSION")]
                    )
                    print("✅ 已自动更新 GH_SESSION Secret（下次可直接使用）")
                except Exception as e:
                    print(f"⚠️  自动更新 Secret 失败: {e}")

            if notifier:
                notifier.notify(
                    f"✅ GitHub 登录成功\n🍪 Session: {session_cookie[:20]}...\n💾 已更新 Secret",
                    level="SUCCESS"
                )

            browser.close()
            sys.exit(0)

        except Exception as e:
            print(f"❌ 登录过程出错: {e}")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"login_failed_{timestamp}.png"
            page.screenshot(path=screenshot_path, full_page=True)

            output_to_github_actions("", "failed")

            if notifier:
                notifier.notify(f"❌ 登录失败: {e}", level="ERROR")
                notifier.send_photo(screenshot_path, "登录失败截图")

            browser.close()
            sys.exit(1)


if __name__ == "__main__":
    main()
