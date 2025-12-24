"""状态持久化管理"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class StateManager:
    """状态管理器，用于持久化登录状态和统计信息"""
    
    def __init__(self, state_file: str = ".athena_state.json"):
        """初始化状态管理器
        
        Args:
            state_file: 状态文件路径
        """
        self.state_file = Path(state_file)
        self.state: Dict[str, Any] = self._load()
    
    def _load(self) -> Dict[str, Any]:
        """加载状态文件"""
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"加载状态文件失败: {e}，使用空状态")
                return {}
        return {}
    
    def save(self) -> None:
        """保存状态到文件"""
        try:
            self.state_file.write_text(
                json.dumps(self.state, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
        except IOError as e:
            logger.error(f"保存状态文件失败: {e}")
    
    def record_login_attempt(
        self,
        site: str,
        success: bool,
        error_message: str = "",
        two_factor_used: bool = False,
        device_verification_used: bool = False
    ) -> None:
        """记录登录尝试
        
        Args:
            site: 站点名称
            success: 是否成功
            error_message: 错误消息（如果失败）
            two_factor_used: 是否使用了双因素认证
            device_verification_used: 是否使用了设备验证
        """
        if site not in self.state:
            self.state[site] = {
                'total_attempts': 0,
                'total_successes': 0,
                'total_failures': 0,
                'consecutive_failures': 0
            }
        
        site_state = self.state[site]
        
        # 更新统计
        site_state['total_attempts'] += 1
        site_state['last_attempt_time'] = datetime.now().isoformat()
        site_state['last_attempt_success'] = success
        
        if success:
            site_state['total_successes'] += 1
            site_state['consecutive_failures'] = 0
            site_state['last_success_time'] = datetime.now().isoformat()
            site_state['two_factor_used'] = two_factor_used
            site_state['device_verification_used'] = device_verification_used
        else:
            site_state['total_failures'] += 1
            site_state['consecutive_failures'] = site_state.get('consecutive_failures', 0) + 1
            site_state['last_error'] = error_message
        
        self.save()
    
    def get_site_state(self, site: str) -> Optional[Dict[str, Any]]:
        """获取站点状态
        
        Args:
            site: 站点名称
            
        Returns:
            站点状态字典，如果不存在返回 None
        """
        return self.state.get(site)
    
    def is_healthy(self, site: str, max_consecutive_failures: int = 3) -> bool:
        """检查站点是否健康
        
        Args:
            site: 站点名称
            max_consecutive_failures: 允许的最大连续失败次数
            
        Returns:
            是否健康
        """
        site_state = self.get_site_state(site)
        if not site_state:
            return True  # 新站点默认健康
        
        consecutive_failures = site_state.get('consecutive_failures', 0)
        return consecutive_failures < max_consecutive_failures
    
    def get_stats(self, site: str) -> str:
        """获取站点统计信息文本
        
        Args:
            site: 站点名称
            
        Returns:
            格式化的统计信息
        """
        site_state = self.get_site_state(site)
        if not site_state:
            return f"站点 {site} 暂无历史记录"
        
        total = site_state.get('total_attempts', 0)
        successes = site_state.get('total_successes', 0)
        failures = site_state.get('total_failures', 0)
        success_rate = (successes / total * 100) if total > 0 else 0
        
        last_success = site_state.get('last_success_time', 'N/A')
        consecutive_failures = site_state.get('consecutive_failures', 0)
        
        return f"""📊 {site} 统计信息：
总尝试次数: {total}
成功次数: {successes}
失败次数: {failures}
成功率: {success_rate:.1f}%
连续失败: {consecutive_failures}
最后成功: {last_success}"""

