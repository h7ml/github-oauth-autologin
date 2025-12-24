"""配置验证器测试"""
import pytest
from pydantic import ValidationError
from core.validators import (
    GitHubCredentialsValidator,
    SiteConfigValidator,
    validate_credentials,
    validate_site_config,
)


class TestGitHubCredentialsValidator:
    """测试 GitHub 凭据验证器"""

    def test_valid_credentials(self):
        """测试有效凭据"""
        creds = GitHubCredentialsValidator(username="test_user", password="password123")
        assert creds.username == "test_user"
        assert creds.password == "password123"

    def test_invalid_short_password(self):
        """测试密码过短"""
        with pytest.raises(ValidationError):
            GitHubCredentialsValidator(username="test", password="short")

    def test_invalid_session_cookie_format(self):
        """测试无效的 Session Cookie 格式"""
        with pytest.raises(ValidationError):
            GitHubCredentialsValidator(
                username="test", password="password123", session_cookie="invalid!@#$%"
            )

    def test_valid_session_cookie(self):
        """测试有效的 Session Cookie"""
        creds = GitHubCredentialsValidator(
            username="test", password="password123", session_cookie="valid_cookie-123_ABC"
        )
        assert creds.session_cookie == "valid_cookie-123_ABC"


class TestSiteConfigValidator:
    """测试站点配置验证器"""

    def test_valid_config(self):
        """测试有效配置"""
        config = SiteConfigValidator(
            name="Test Site",
            login_url="https://example.com/login",
            oauth_button_selectors=['button:has-text("GitHub")'],
            success_url_patterns=["example.com/dashboard"],
        )
        assert config.name == "Test Site"
        assert config.enabled is True

    def test_invalid_login_url(self):
        """测试无效的登录 URL"""
        with pytest.raises(ValidationError):
            SiteConfigValidator(
                name="Test",
                login_url="not-a-url",
                oauth_button_selectors=["button"],
                success_url_patterns=["pattern"],
            )

    def test_empty_selectors(self):
        """测试空选择器列表"""
        with pytest.raises(ValidationError):
            SiteConfigValidator(
                name="Test",
                login_url="https://example.com",
                oauth_button_selectors=[],
                success_url_patterns=["pattern"],
            )


class TestValidateFunctions:
    """测试验证函数"""

    def test_validate_credentials_valid(self):
        """测试有效凭据验证"""
        valid, msg = validate_credentials("user", "password123")
        assert valid is True
        assert msg == ""

    def test_validate_credentials_invalid(self):
        """测试无效凭据验证"""
        valid, msg = validate_credentials("user", "short")
        assert valid is False
        assert "at least 8 characters" in msg

    def test_validate_site_config_valid(self):
        """测试有效站点配置验证"""
        config_data = {
            "name": "Test",
            "login_url": "https://example.com",
            "oauth_button_selectors": ["button"],
            "success_url_patterns": ["pattern"],
        }
        valid, msg = validate_site_config(config_data)
        assert valid is True
        assert msg == ""
