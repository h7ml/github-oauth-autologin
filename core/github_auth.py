"""GitHub 认证器"""
import time
import logging
from typing import Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout, Error as PlaywrightError

from core.types import (
    GitHubCredentials,
    TwoFactorConfig,
    DeviceVerificationConfig,
    NotifierInterface
)
from core.constants import Timeouts, Selectors, GitHubUrls, Messages

logger = logging.getLogger(__name__)


class GitHubAuthenticator:
    """GitHub 认证处理器
    
    负责处理完整的 GitHub 登录流程，包括：
    - 基本凭据认证
    - 双因素认证（GitHub Mobile / TOTP）
    - 设备验证
    - 错误处理和截图
    
    Attributes:
        notifier: 通知器实例，用于发送实时通知和接收用户输入
        screenshots: 截图文件路径列表
    """

    def __init__(self, notifier: NotifierInterface):
        """初始化认证器
        
        Args:
            notifier: 通知器实例
        """
        self.notifier = notifier
        self.screenshots: list[str] = []

    def login(
        self,
        page: Page,
        credentials: GitHubCredentials,
        two_factor_config: TwoFactorConfig,
        device_config: DeviceVerificationConfig
    ) -> bool:
        """完整的 GitHub 登录流程
        
        Args:
            page: Playwright Page 对象
            credentials: GitHub 凭据
            two_factor_config: 双因素认证配置
            device_config: 设备验证配置
            
        Returns:
            是否登录成功
        """
        logger.info("🔹 登录 GitHub...")
        self._screenshot(page, "github_登录页")

        # 输入凭据
        if not self._fill_credentials(page, credentials):
            return False

        self._screenshot(page, "github_已填写")

        # 提交表单
        self._submit_login_form(page)

        time.sleep(Timeouts.LOGIN_SLEEP / 1000)
        self._wait_for_page_load(page)
        self._screenshot(page, "github_登录后")

        url = page.url
        logger.info(f"当前 URL: {url}")

        # 处理设备验证
        if GitHubUrls.DEVICE_VERIFICATION in url or GitHubUrls.DEVICE_VERIFICATION_ALT in url:
            if not self.handle_device_verification(page, device_config):
                return False
            time.sleep(2)
            self._wait_for_page_load(page)

        # 处理双因素认证
        if GitHubUrls.TWO_FACTOR in page.url:
            if not self.handle_2fa(page, two_factor_config):
                return False

        # 检查错误
        if self._check_login_error(page):
            return False

        logger.info("✅ GitHub 认证成功")
        return True

    def _fill_credentials(self, page: Page, credentials: GitHubCredentials) -> bool:
        """填写登录凭据
        
        Args:
            page: Page 对象
            credentials: 凭据
            
        Returns:
            是否成功
        """
        try:
            page.locator(Selectors.LOGIN_INPUT).fill(credentials.username)
            page.locator(Selectors.PASSWORD_INPUT).fill(credentials.password)
            logger.info("✅ 已输入凭据")
            return True
        except (PlaywrightTimeout, PlaywrightError) as e:
            logger.error(f"❌ 输入凭据失败: {e}")
            return False

    def _submit_login_form(self, page: Page) -> None:
        """提交登录表单"""
        try:
            page.locator(Selectors.SUBMIT_BUTTON).first.click()
        except (PlaywrightTimeout, PlaywrightError):
            logger.warning("未找到提交按钮，可能已自动提交")

    def _wait_for_page_load(self, page: Page, timeout: int = Timeouts.NETWORK_IDLE) -> None:
        """等待页面加载完成"""
        try:
            page.wait_for_load_state('networkidle', timeout=timeout)
        except PlaywrightTimeout:
            logger.warning("页面加载超时，继续执行")

    def _check_login_error(self, page: Page) -> bool:
        """检查登录错误
        
        Returns:
            是否有错误
        """
        try:
            err = page.locator(Selectors.ERROR_FLASH).first
            if err.is_visible(timeout=2000):
                error_text = err.inner_text()
                logger.error(f"❌ 登录错误: {error_text}")
                return True
        except (PlaywrightTimeout, PlaywrightError):
            pass
        return False

    def handle_device_verification(
        self,
        page: Page,
        config: DeviceVerificationConfig
    ) -> bool:
        """处理设备验证
        
        Args:
            page: Page 对象
            config: 设备验证配置
            
        Returns:
            是否成功
        """
        logger.warning(f"⚠️ 需要设备验证，等待 {config.wait} 秒...")
        self._screenshot(page, "设备验证")

        self.notifier.notify(
            Messages.DEVICE_VERIFICATION_NEEDED.format(wait=config.wait),
            "WARN"
        )

        if self.screenshots:
            self.notifier.send_photo(self.screenshots[-1], "设备验证页面")

        for i in range(config.wait):
            time.sleep(1)
            if i % 5 == 0 and i > 0:
                logger.info(f"  等待... ({i}/{config.wait}秒)")
                url = page.url
                if GitHubUrls.DEVICE_VERIFICATION not in url and \
                   GitHubUrls.DEVICE_VERIFICATION_ALT not in url:
                    logger.info("✅ 设备验证通过！")
                    self.notifier.notify("✅ <b>设备验证通过</b>", "SUCCESS")
                    return True
                try:
                    page.reload(timeout=10000)
                    self._wait_for_page_load(page, 10000)
                except (PlaywrightTimeout, PlaywrightError):
                    pass

        # 最后检查一次
        if GitHubUrls.DEVICE_VERIFICATION not in page.url and \
           GitHubUrls.DEVICE_VERIFICATION_ALT not in page.url:
            return True

        logger.error("❌ 设备验证超时")
        self.notifier.notify("❌ <b>设备验证超时</b>", "ERROR")
        return False

    def handle_2fa(self, page: Page, config: TwoFactorConfig) -> bool:
        """处理双因素认证（自动路由）
        
        Args:
            page: Page 对象
            config: 2FA 配置
            
        Returns:
            是否成功
        """
        logger.warning("⚠️ 需要双因素认证")
        self._screenshot(page, "双因素认证")

        if GitHubUrls.TWO_FACTOR_MOBILE in page.url:
            return self._handle_2fa_mobile(page, config.mobile_wait)
        else:
            return self._handle_2fa_totp(page, config.totp_wait)

    def _handle_2fa_mobile(self, page: Page, timeout: int) -> bool:
        """处理 GitHub Mobile 验证
        
        Args:
            page: Page 对象
            timeout: 超时时间（秒）
            
        Returns:
            是否成功
        """
        logger.warning(f"⚠️ 等待 GitHub Mobile 批准（{timeout}秒）...")

        shot = self._screenshot(page, "2fa_mobile")
        self.notifier.notify(
            Messages.TWO_FACTOR_MOBILE_NEEDED.format(timeout=timeout),
            "WARN"
        )

        if shot:
            self.notifier.send_photo(shot, "双因素认证页面")

        for i in range(timeout):
            time.sleep(1)

            url = page.url
            if GitHubUrls.TWO_FACTOR not in url:
                logger.info("✅ 双因素认证通过！")
                self.notifier.notify("✅ <b>双因素认证通过</b>", "SUCCESS")
                return True

            if GitHubUrls.LOGIN in url:
                logger.error("❌ 被重定向到登录页")
                return False

            if i % 10 == 0 and i != 0:
                logger.info(f"  等待... ({i}/{timeout}秒)")

        logger.error("❌ 双因素认证超时")
        self.notifier.notify("❌ <b>双因素认证超时</b>", "ERROR")
        return False

    def _handle_2fa_totp(self, page: Page, timeout: int) -> bool:
        """处理 TOTP 验证码
        
        Args:
            page: Page 对象
            timeout: 超时时间（秒）
            
        Returns:
            是否成功
        """
        logger.warning("🔐 需要输入验证码")
        shot = self._screenshot(page, "2fa_totp")

        self.notifier.notify(
            Messages.TWO_FACTOR_TOTP_NEEDED.format(timeout=timeout),
            "WARN"
        )

        if shot:
            self.notifier.send_photo(shot, "验证码输入页面")

        code = self.notifier.wait_user_input(
            "请输入验证码",
            r"^/code\s+(\d{6,8})$",
            timeout
        )

        if not code:
            logger.error("❌ 等待验证码超时")
            self.notifier.notify("❌ <b>等待验证码超时</b>", "ERROR")
            return False

        logger.info("✅ 收到验证码，正在填入...")
        self.notifier.notify("✅ 收到验证码，正在填入...", "SUCCESS")

        return self._fill_totp_code(page, code)

    def _fill_totp_code(self, page: Page, code: str) -> bool:
        """填写 TOTP 验证码
        
        Args:
            page: Page 对象
            code: 验证码
            
        Returns:
            是否成功
        """
        for sel in Selectors.TOTP_INPUT:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=2000):
                    el.fill(code)
                    logger.info("✅ 已填入验证码")
                    time.sleep(1)

                    # 提交
                    try:
                        btn = page.locator('button[type="submit"]').first
                        btn.click()
                    except (PlaywrightTimeout, PlaywrightError):
                        page.keyboard.press("Enter")

                    time.sleep(3)
                    self._wait_for_page_load(page)

                    if GitHubUrls.TWO_FACTOR not in page.url:
                        logger.info("✅ 验证码验证通过！")
                        self.notifier.notify("✅ <b>验证码验证通过</b>", "SUCCESS")
                        return True
                    else:
                        logger.error("❌ 验证码可能错误")
                        self.notifier.notify("❌ <b>验证码错误</b>", "ERROR")
                        return False
            except (PlaywrightTimeout, PlaywrightError):
                continue

        logger.error("❌ 未找到验证码输入框")
        return False

    def _screenshot(self, page: Page, name: str) -> Optional[str]:
        """截图
        
        Args:
            page: Page 对象
            name: 截图名称
            
        Returns:
            截图文件路径，失败返回 None
        """
        try:
            n = len(self.screenshots) + 1
            filename = f"{n:02d}_{name}.png"
            page.screenshot(path=filename)
            self.screenshots.append(filename)
            logger.debug(f"截图保存: {filename}")
            return filename
        except (PlaywrightTimeout, PlaywrightError) as e:
            logger.warning(f"截图失败: {e}")
            return None
