"""GitHub 认证器"""
import time
from typing import Optional
from core.types import GitHubCredentials, TwoFactorConfig, DeviceVerificationConfig, NotifierInterface


class GitHubAuthenticator:
    """GitHub 认证处理器"""

    def __init__(self, notifier: NotifierInterface):
        self.notifier = notifier
        self.screenshots = []

    def login(
        self,
        page,
        credentials: GitHubCredentials,
        two_factor_config: TwoFactorConfig,
        device_config: DeviceVerificationConfig
    ) -> bool:
        """完整的 GitHub 登录流程"""
        self._log("登录 GitHub...", "STEP")
        self._screenshot(page, "github_登录页")

        # 输入凭据
        try:
            page.locator('input[name="login"]').fill(credentials.username)
            page.locator('input[name="password"]').fill(credentials.password)
            self._log("已输入凭据", "SUCCESS")
        except Exception as e:
            self._log(f"输入失败: {e}", "ERROR")
            return False

        self._screenshot(page, "github_已填写")

        # 提交表单
        try:
            page.locator('input[type="submit"], button[type="submit"]').first.click()
        except Exception:
            pass

        time.sleep(3)
        page.wait_for_load_state('networkidle', timeout=30000)
        self._screenshot(page, "github_登录后")

        url = page.url
        self._log(f"当前 URL: {url}", "INFO")

        # 处理设备验证
        if 'verified-device' in url or 'device-verification' in url:
            if not self.handle_device_verification(page, device_config):
                return False
            time.sleep(2)
            page.wait_for_load_state('networkidle', timeout=30000)

        # 处理双因素认证
        if 'two-factor' in page.url:
            if not self.handle_2fa(page, two_factor_config):
                return False

        # 检查错误
        try:
            err = page.locator('.flash-error').first
            if err.is_visible(timeout=2000):
                self._log(f"错误: {err.inner_text()}", "ERROR")
                return False
        except Exception:
            pass

        return True

    def handle_device_verification(self, page, config: DeviceVerificationConfig) -> bool:
        """处理设备验证"""
        self._log(f"需要设备验证，等待 {config.wait} 秒...", "WARN")
        self._screenshot(page, "设备验证")

        self.notifier.notify(f"""⚠️ <b>需要设备验证</b>

请在 {config.wait} 秒内批准：
1️⃣ 检查邮箱点击链接
2️⃣ 或在 GitHub App 批准""", "WARN")

        if self.screenshots:
            self.notifier.send_photo(self.screenshots[-1], "设备验证页面")

        for i in range(config.wait):
            time.sleep(1)
            if i % 5 == 0:
                self._log(f"  等待... ({i}/{config.wait}秒)", "INFO")
                url = page.url
                if 'verified-device' not in url and 'device-verification' not in url:
                    self._log("设备验证通过！", "SUCCESS")
                    self.notifier.notify("✅ <b>设备验证通过</b>", "SUCCESS")
                    return True
                try:
                    page.reload(timeout=10000)
                    page.wait_for_load_state('networkidle', timeout=10000)
                except Exception:
                    pass

        if 'verified-device' not in page.url:
            return True

        self._log("设备验证超时", "ERROR")
        self.notifier.notify("❌ <b>设备验证超时</b>", "ERROR")
        return False

    def handle_2fa(self, page, config: TwoFactorConfig) -> bool:
        """处理双因素认证（自动路由）"""
        self._log("需要双因素认证", "WARN")
        self._screenshot(page, "双因素认证")

        if 'two-factor/mobile' in page.url:
            return self._handle_2fa_mobile(page, config.mobile_wait)
        else:
            return self._handle_2fa_totp(page, config.totp_wait)

    def _handle_2fa_mobile(self, page, timeout: int) -> bool:
        """处理 GitHub Mobile 验证"""
        self._log(f"等待 GitHub Mobile 批准（{timeout}秒）...", "WARN")

        shot = self._screenshot(page, "2fa_mobile")
        self.notifier.notify(f"""⚠️ <b>需要双因素认证（GitHub Mobile）</b>

请打开手机 GitHub App 批准本次登录。
等待时间：{timeout} 秒""", "WARN")

        if shot:
            self.notifier.send_photo(shot, "双因素认证页面")

        for i in range(timeout):
            time.sleep(1)

            url = page.url
            if "github.com/sessions/two-factor/" not in url:
                self._log("双因素认证通过！", "SUCCESS")
                self.notifier.notify("✅ <b>双因素认证通过</b>", "SUCCESS")
                return True

            if "github.com/login" in url:
                self._log("被重定向到登录页", "ERROR")
                return False

            if i % 10 == 0 and i != 0:
                self._log(f"  等待... ({i}/{timeout}秒)", "INFO")

        self._log("双因素认证超时", "ERROR")
        self.notifier.notify("❌ <b>双因素认证超时</b>", "ERROR")
        return False

    def _handle_2fa_totp(self, page, timeout: int) -> bool:
        """处理 TOTP 验证码"""
        self._log("需要输入验证码", "WARN")
        shot = self._screenshot(page, "2fa_totp")

        self.notifier.notify(f"""🔐 <b>需要验证码</b>

请在 Telegram 发送：
<code>/code 你的6位验证码</code>

等待时间：{timeout} 秒""", "WARN")

        if shot:
            self.notifier.send_photo(shot, "验证码输入页面")

        code = self.notifier.wait_user_input(
            "请输入验证码",
            r"^/code\s+(\d{6,8})$",
            timeout
        )

        if not code:
            self._log("等待验证码超时", "ERROR")
            self.notifier.notify("❌ <b>等待验证码超时</b>", "ERROR")
            return False

        self._log("收到验证码，正在填入...", "SUCCESS")
        self.notifier.notify("✅ 收到验证码，正在填入...", "SUCCESS")

        selectors = [
            'input[autocomplete="one-time-code"]',
            'input[name="app_otp"]',
            'input[name="otp"]'
        ]

        for sel in selectors:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=2000):
                    el.fill(code)
                    self._log("已填入验证码", "SUCCESS")
                    time.sleep(1)

                    # 提交
                    try:
                        btn = page.locator('button[type="submit"]').first
                        btn.click()
                    except Exception:
                        page.keyboard.press("Enter")

                    time.sleep(3)
                    page.wait_for_load_state('networkidle', timeout=30000)

                    if "github.com/sessions/two-factor/" not in page.url:
                        self._log("验证码验证通过！", "SUCCESS")
                        self.notifier.notify("✅ <b>验证码验证通过</b>", "SUCCESS")
                        return True
                    else:
                        self._log("验证码可能错误", "ERROR")
                        self.notifier.notify("❌ <b>验证码错误</b>", "ERROR")
                        return False
            except Exception:
                pass

        self._log("未找到验证码输入框", "ERROR")
        return False

    def _log(self, msg: str, level: str = "INFO"):
        """记录日志"""
        icons = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARN": "⚠️", "STEP": "🔹"}
        print(f"{icons.get(level, '•')} {msg}")

    def _screenshot(self, page, name: str) -> Optional[str]:
        """截图"""
        try:
            n = len(self.screenshots) + 1
            filename = f"{n:02d}_{name}.png"
            page.screenshot(path=filename)
            self.screenshots.append(filename)
            return filename
        except Exception:
            return None
