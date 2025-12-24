"""OAuth 流程控制器"""
import time


class OAuthFlowController:
    """OAuth 流程控制"""

    def __init__(self, notifier):
        self.notifier = notifier

    def click_oauth_button(self, page, selectors: list[str], button_name: str = "OAuth") -> bool:
        """点击 OAuth 登录按钮"""
        for selector in selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=3000):
                    element.click()
                    print(f"✅ 已点击: {button_name}")
                    return True
            except Exception:
                pass

        print(f"❌ 未找到 {button_name} 按钮")
        return False

    def handle_authorization(self, page) -> bool:
        """处理 OAuth 授权页面"""
        if "github.com/login/oauth/authorize" not in page.url:
            return True

        print("🔹 处理 OAuth 授权...")

        authorize_selectors = [
            'button[name="authorize"]',
            'button:has-text("Authorize")',
            'button:has-text("授权")',
        ]

        for selector in authorize_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=2000):
                    element.click()
                    print("✅ 已点击授权按钮")
                    time.sleep(3)
                    page.wait_for_load_state("networkidle", timeout=30000)
                    return True
            except Exception:
                pass

        return True

    def wait_callback(self, page, success_patterns: list[str], timeout: int = 60) -> bool:
        """等待 OAuth 回调完成"""
        print(f"🔹 等待回调重定向（{timeout}秒）...")

        for i in range(timeout):
            url = page.url

            # 检查成功模式
            for pattern in success_patterns:
                if pattern.startswith("!"):
                    # 反向匹配（不包含）
                    if pattern[1:] not in url:
                        continue
                else:
                    # 正向匹配
                    if pattern in url:
                        print("✅ 回调成功！")
                        return True

            # 处理 OAuth 授权页面
            if "github.com/login/oauth/authorize" in url:
                self.handle_authorization(page)

            time.sleep(1)
            if i % 10 == 0 and i > 0:
                print(f"  等待... ({i}/{timeout}秒)")

        print("❌ 回调超时")
        return False
