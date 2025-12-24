"""配置验证器"""
import re
from typing import Tuple, List
from pydantic import BaseModel, Field, field_validator, ConfigDict


class GitHubCredentialsValidator(BaseModel):
    """GitHub 凭据验证器"""

    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(..., min_length=1, description="GitHub 用户名")
    password: str = Field(..., min_length=8, description="GitHub 密码")
    session_cookie: str | None = Field(None, description="GitHub Session Cookie")

    @field_validator("session_cookie")
    @classmethod
    def validate_session_cookie(cls, v: str | None) -> str | None:
        """验证 Session Cookie 格式"""
        if v and not re.match(r"^[A-Za-z0-9_-]+$", v):
            raise ValueError("Session Cookie 格式无效")
        return v


class TwoFactorConfigValidator(BaseModel):
    """双因素认证配置验证器"""

    strategy: str = Field("auto", pattern="^(auto|mobile|totp)$")
    mobile_wait: int = Field(120, ge=30, le=300)
    totp_wait: int = Field(120, ge=30, le=300)


class TimeoutConfigValidator(BaseModel):
    """超时配置验证器"""

    page_load: int = Field(30, ge=10, le=120)
    oauth_callback: int = Field(60, ge=30, le=300)
    network_idle: int = Field(15, ge=5, le=60)


class SiteConfigValidator(BaseModel):
    """站点配置验证器"""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1)
    enabled: bool = Field(True)
    login_url: str = Field(..., pattern=r"^https?://.+")
    oauth_button_selectors: List[str] = Field(..., min_length=1)
    success_url_patterns: List[str] = Field(..., min_length=1)
    two_factor: TwoFactorConfigValidator = Field(default_factory=TwoFactorConfigValidator)
    timeouts: TimeoutConfigValidator = Field(default_factory=TimeoutConfigValidator)
    cookie_domain: str = Field("github.com")
    cookie_names: List[str] = Field(default_factory=lambda: ["user_session"])

    @field_validator("login_url")
    @classmethod
    def validate_login_url(cls, v: str) -> str:
        """验证登录 URL"""
        if not v.startswith(("http://", "https://")):
            raise ValueError("login_url 必须是完整的 HTTP/HTTPS URL")
        return v

    @field_validator("oauth_button_selectors")
    @classmethod
    def validate_selectors(cls, v: List[str]) -> List[str]:
        """验证选择器列表"""
        if not v:
            raise ValueError("至少需要一个 OAuth 按钮选择器")
        return v


def validate_credentials(
    username: str, password: str, session_cookie: str = ""
) -> Tuple[bool, str]:
    """验证 GitHub 凭据

    Args:
        username: GitHub 用户名
        password: GitHub 密码
        session_cookie: Session Cookie（可选）

    Returns:
        (是否有效, 错误消息)
    """
    try:
        GitHubCredentialsValidator(
            username=username,
            password=password,
            session_cookie=session_cookie if session_cookie else None,
        )
        return True, ""
    except Exception as e:
        return False, str(e)


def validate_site_config(config_data: dict) -> Tuple[bool, str]:
    """验证站点配置

    Args:
        config_data: 配置字典

    Returns:
        (是否有效, 错误消息)
    """
    try:
        SiteConfigValidator(**config_data)
        return True, ""
    except Exception as e:
        return False, str(e)
