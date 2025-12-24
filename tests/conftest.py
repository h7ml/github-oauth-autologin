"""Pytest 配置和 Fixtures"""
import pytest
from unittest.mock import Mock
from core.types import GitHubCredentials, TwoFactorConfig, DeviceVerificationConfig


@pytest.fixture
def mock_credentials():
    """模拟 GitHub 凭据"""
    return GitHubCredentials(
        username="test_user",
        password="test_password_123",
        session_cookie="test_session_cookie_abc123",
    )


@pytest.fixture
def mock_two_factor_config():
    """模拟 2FA 配置"""
    return TwoFactorConfig(strategy="auto", mobile_wait=120, totp_wait=120)


@pytest.fixture
def mock_device_config():
    """模拟设备验证配置"""
    return DeviceVerificationConfig(wait=30)


@pytest.fixture
def mock_notifier():
    """模拟通知器"""
    notifier = Mock()
    notifier.notify = Mock()
    notifier.send_photo = Mock()
    notifier.wait_user_input = Mock(return_value=None)
    return notifier


@pytest.fixture
def mock_playwright_page():
    """模拟 Playwright Page"""
    page = Mock()
    page.url = "https://github.com"
    page.goto = Mock()
    page.wait_for_load_state = Mock()
    page.locator = Mock()
    page.screenshot = Mock()
    return page


@pytest.fixture
def mock_browser_context():
    """模拟 Playwright BrowserContext"""
    context = Mock()
    context.cookies = Mock(return_value=[])
    context.add_cookies = Mock()
    return context
