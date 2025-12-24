"""状态管理器测试"""
import pytest
import json
from pathlib import Path
from core.state_manager import StateManager


class TestStateManager:
    """测试状态管理器"""

    @pytest.fixture
    def state_file(self, tmp_path):
        """临时状态文件"""
        return tmp_path / "test_state.json"

    @pytest.fixture
    def state_manager(self, state_file):
        """创建状态管理器实例"""
        return StateManager(str(state_file))

    def test_init_empty_state(self, state_manager):
        """测试初始化空状态"""
        assert state_manager.state == {}

    def test_record_login_success(self, state_manager):
        """测试记录成功登录"""
        state_manager.record_login_attempt(
            site="test_site",
            success=True,
            two_factor_used=True
        )

        site_state = state_manager.get_site_state("test_site")
        assert site_state is not None
        assert site_state['total_attempts'] == 1
        assert site_state['total_successes'] == 1
        assert site_state['consecutive_failures'] == 0
        assert site_state['two_factor_used'] is True

    def test_record_login_failure(self, state_manager):
        """测试记录失败登录"""
        state_manager.record_login_attempt(
            site="test_site",
            success=False,
            error_message="Test error"
        )

        site_state = state_manager.get_site_state("test_site")
        assert site_state['total_failures'] == 1
        assert site_state['consecutive_failures'] == 1
        assert site_state['last_error'] == "Test error"

    def test_consecutive_failures(self, state_manager):
        """测试连续失败计数"""
        # 失败两次
        state_manager.record_login_attempt("test_site", False)
        state_manager.record_login_attempt("test_site", False)

        site_state = state_manager.get_site_state("test_site")
        assert site_state['consecutive_failures'] == 2

        # 成功一次应重置
        state_manager.record_login_attempt("test_site", True)
        site_state = state_manager.get_site_state("test_site")
        assert site_state['consecutive_failures'] == 0

    def test_is_healthy(self, state_manager):
        """测试健康检查"""
        # 新站点默认健康
        assert state_manager.is_healthy("new_site") is True

        # 失败少于阈值
        state_manager.record_login_attempt("test_site", False)
        state_manager.record_login_attempt("test_site", False)
        assert state_manager.is_healthy("test_site", max_consecutive_failures=3) is True

        # 失败达到阈值
        state_manager.record_login_attempt("test_site", False)
        assert state_manager.is_healthy("test_site", max_consecutive_failures=3) is False

    def test_persistence(self, state_file, state_manager):
        """测试状态持久化"""
        state_manager.record_login_attempt("test_site", True)
        state_manager.save()

        # 重新加载
        new_manager = StateManager(str(state_file))
        site_state = new_manager.get_site_state("test_site")
        assert site_state is not None
        assert site_state['total_successes'] == 1

    def test_get_stats(self, state_manager):
        """测试统计信息"""
        state_manager.record_login_attempt("test_site", True)
        state_manager.record_login_attempt("test_site", False)

        stats = state_manager.get_stats("test_site")
        assert "总尝试次数: 2" in stats
        assert "成功次数: 1" in stats
        assert "失败次数: 1" in stats
        assert "成功率: 50.0%" in stats

