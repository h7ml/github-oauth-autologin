"""核心类型定义"""
from dataclasses import dataclass, field
from typing import Optional, Protocol, Literal
from abc import ABC, abstractmethod


@dataclass
class GitHubCredentials:
    """GitHub 凭据"""
    username: str
    password: str
    session_cookie: Optional[str] = None


@dataclass
class TwoFactorConfig:
    """双因素认证配置"""
    strategy: Literal["auto", "mobile", "totp"] = "auto"
    mobile_wait: int = 120
    totp_wait: int = 120


@dataclass
class DeviceVerificationConfig:
    """设备验证配置"""
    wait: int = 30


@dataclass
class TimeoutConfig:
    """超时配置"""
    page_load: int = 30
    oauth_callback: int = 60
    network_idle: int = 15


@dataclass
class CookieTarget:
    """Cookie 存储目标"""
    type: Literal["github_secret", "file", "env"]
    secret_name: Optional[str] = None
    path: Optional[str] = None
    encrypt: bool = False


@dataclass
class KeepAliveURL:
    """保活 URL"""
    url: str
    name: str


@dataclass
class SiteConfig:
    """站点配置"""
    name: str
    enabled: bool
    login_url: str
    success_url_patterns: list[str]
    oauth_button_selectors: list[str]
    two_factor: TwoFactorConfig
    device_verification: DeviceVerificationConfig
    timeouts: TimeoutConfig
    keepalive_urls: list[KeepAliveURL] = field(default_factory=list)
    cookie_domain: str = "github.com"
    cookie_names: list[str] = field(default_factory=lambda: ["user_session"])
    cookie_targets: list[CookieTarget] = field(default_factory=list)


class NotifierInterface(ABC):
    """通知器接口"""

    @abstractmethod
    def notify(self, message: str, level: str = "INFO", attachments: list[str] = None):
        """发送通知"""
        pass

    @abstractmethod
    def wait_user_input(self, prompt: str, pattern: str, timeout: int = 120) -> Optional[str]:
        """等待用户输入"""
        pass

    @abstractmethod
    def send_photo(self, path: str, caption: str = ""):
        """发送图片"""
        pass
