"""Cookie 管理器测试"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from core.cookie_manager import CookieManager
from core.types import CookieTarget


class TestCookieManager:
    """测试 Cookie 管理器"""

    @pytest.fixture
    def cookie_manager(self, mock_notifier):
        """创建 Cookie 管理器实例"""
        return CookieManager(mock_notifier)

    def test_extract_session_success(self, cookie_manager, mock_browser_context):
        """测试成功提取 Session Cookie"""
        mock_browser_context.cookies.return_value = [
            {"name": "user_session", "value": "test_session_value", "domain": ".github.com"}
        ]

        result = cookie_manager.extract_session(mock_browser_context)
        assert result == "test_session_value"

    def test_extract_session_not_found(self, cookie_manager, mock_browser_context):
        """测试 Cookie 不存在"""
        mock_browser_context.cookies.return_value = []

        result = cookie_manager.extract_session(mock_browser_context)
        assert result is None

    def test_extract_session_wrong_domain(self, cookie_manager, mock_browser_context):
        """测试域名不匹配"""
        mock_browser_context.cookies.return_value = [
            {"name": "user_session", "value": "test_value", "domain": "example.com"}
        ]

        result = cookie_manager.extract_session(mock_browser_context)
        assert result is None

    def test_save_cookies_file_target(self, cookie_manager, tmp_path):
        """测试保存到文件"""
        file_path = tmp_path / "test_cookie.json"
        targets = [CookieTarget(type="file", path=str(file_path))]

        cookie_manager.save_cookies("test_value", targets)

        assert file_path.exists()

    def test_save_cookies_empty_value(self, cookie_manager):
        """测试空值不保存"""
        targets = [CookieTarget(type="env", secret_name="TEST")]

        # 不应抛出异常
        cookie_manager.save_cookies("", targets)

    @patch("core.cookie_manager.requests.get")
    @patch("core.cookie_manager.requests.put")
    def test_save_to_github_secret_success(self, mock_put, mock_get, cookie_manager, monkeypatch):
        """测试成功更新 GitHub Secret"""
        monkeypatch.setenv("REPO_TOKEN", "test_token")
        monkeypatch.setenv("GITHUB_REPOSITORY", "user/repo")

        # Mock 公钥响应 (32字节密钥的 base64 编码)
        import base64

        dummy_key = b"x" * 32  # 32 bytes key
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "key": base64.b64encode(dummy_key).decode(),
            "key_id": "test_key_id",
        }
        mock_get.return_value.raise_for_status = Mock()

        # Mock 更新响应
        mock_put.return_value.status_code = 204
        mock_put.return_value.raise_for_status = Mock()

        targets = [CookieTarget(type="github_secret", secret_name="GH_SESSION")]

        # 注意：实际测试中可能需要 mock nacl 库
        try:
            cookie_manager.save_cookies("test_value", targets)
        except ImportError:
            # nacl 库未安装时跳过
            pytest.skip("pynacl not installed")
