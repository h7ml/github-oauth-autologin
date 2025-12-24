"""安全工具测试"""
import pytest
from utils.security import mask_sensitive, sanitize_log_message


class TestMaskSensitive:
    """测试敏感信息遮蔽"""

    def test_mask_normal_string(self):
        """测试正常字符串遮蔽"""
        result = mask_sensitive("abcdefghijklmnopqrstuvwxyz", 4)
        assert result == "abcd******************wxyz"

    def test_mask_short_string(self):
        """测试短字符串完全遮蔽"""
        result = mask_sensitive("abc", 4)
        assert result == "***"

    def test_mask_empty_string(self):
        """测试空字符串"""
        result = mask_sensitive("", 4)
        assert result == ""

    def test_mask_custom_show_chars(self):
        """测试自定义显示字符数"""
        result = mask_sensitive("1234567890", 2)
        assert result == "12******90"


class TestSanitizeLogMessage:
    """测试日志消息清理"""

    def test_sanitize_cookie(self):
        """测试遮蔽 Cookie"""
        message = 'cookie: "abcdefghijklmnopqrstuvwxyz"'
        result = sanitize_log_message(message)
        assert "abcdef" in result
        assert "*" in result
        assert "uvwxyz" in result

    def test_sanitize_password(self):
        """测试遮蔽密码"""
        message = "password: my_secret_password_123"
        result = sanitize_log_message(message)
        assert "********" in result
        assert "my_secret_password" not in result

    def test_no_sanitization_needed(self):
        """测试无需清理的消息"""
        message = "Login successful"
        result = sanitize_log_message(message)
        assert result == message
