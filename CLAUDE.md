# HaloLight Athena - GitHub OAuth 自动登录框架

**作者**: [h7ml](https://github.com/h7ml)
**仓库**: https://github.com/h7ml/github-oauth-autologin
**邮箱**: h7ml@qq.com

---

## 项目概述

**项目定位**：通用的 GitHub OAuth 自动登录工具，通过配置驱动支持任意使用 GitHub OAuth 的 SaaS 平台。

**核心价值**：
1. 配置驱动：无需修改代码即可支持新站点
2. 完善的 2FA 处理：设备验证 + GitHub Mobile + TOTP
3. 智能化通知：Telegram 实时反馈 + 双向通信
4. 自动化运维：GitHub Actions 定时保活

## 架构设计

### 分层结构

```
┌─────────────────────────────────┐
│   CLI / GitHub Actions          │  入口层
├─────────────────────────────────┤
│   Site Adapter (站点适配器)      │  业务层
├─────────────────────────────────┤
│   Core Modules                  │  核心层
│   ├── GitHub Auth (2FA 处理)    │
│   ├── OAuth Handler             │
│   ├── Cookie Manager            │
│   └── Notifier Interface        │
├─────────────────────────────────┤
│   Playwright (浏览器自动化)      │  基础设施层
└─────────────────────────────────┘
```

### 核心设计模式

1. **策略模式**：`NotifierInterface` 支持多种通知渠道（Telegram/Email/Webhook）
2. **模板方法**：`SiteAdapter.run()` 定义登录流程骨架，子类可覆盖特定步骤
3. **配置驱动**：YAML 配置文件驱动站点行为，避免硬编码

## 模块说明

### 1. `core/github_auth.py` - GitHub 认证器

**职责**：处理 GitHub 登录 + 完整的 2FA 流程

**关键方法**：
- `login()`: 主登录流程
- `handle_device_verification()`: 设备验证（邮箱/App 确认）
- `handle_2fa()`: 双因素认证路由器
  - `_handle_2fa_mobile()`: GitHub Mobile 批准
  - `_handle_2fa_totp()`: TOTP 验证码输入

**技术亮点**：
- 智能等待策略：避免频繁刷新导致流程中断
- 实时截图反馈：通过 Telegram 发送关键步骤截图
- 验证码交互：通过 Telegram 接收用户输入的 TOTP

### 2. `core/oauth_handler.py` - OAuth 流程控制

**职责**：处理 OAuth 授权流程

**关键方法**：
- `click_oauth_button()`: 点击站点的 GitHub 登录按钮
- `handle_authorization()`: 处理 GitHub 授权页面
- `wait_callback()`: 等待 OAuth 回调完成

**技术细节**：
- 支持多选择器策略（不同站点按钮可能不同）
- 反向 URL 匹配（`!signin` 表示 URL 不包含 signin）

### 3. `core/cookie_manager.py` - Cookie 管理器

**职责**：提取、加密、存储 Cookie

**存储目标**：
1. **GitHub Secret**：使用 NaCl 加密后更新到 Actions Secrets
2. **本地文件**：JSON 格式存储（可选加密）
3. **环境变量**：仅提示用户手动设置

**安全措施**：
- 使用 `pynacl` 进行 Box 加密
- 只提取必要的 Cookie（`user_session`）

### 4. `sites/base.py` - 站点适配器基类

**职责**：封装完整的登录流程

**生命周期**：
```python
run() ->
  _load_session_cookie() ->      # 1. 预加载已有 Cookie
  访问登录页 ->                   # 2. 导航到站点
  _check_already_logged_in() ->  # 3. 检查是否已登录
  点击 OAuth 按钮 ->              # 4. 触发 GitHub OAuth
  GitHub 认证 ->                 # 5. 处理 GitHub 登录 + 2FA
  等待回调 ->                     # 6. OAuth 回调重定向
  _do_post_login() ->            # 7. 保活操作
  _extract_and_save_cookies()    # 8. 提取并保存 Cookie
```

**扩展点**：
- 子类可覆盖 `_check_already_logged_in()` 实现自定义登录检测
- 子类可覆盖 `_do_post_login()` 实现站点特定的登录后操作

## 配置文件详解

### `config/sites.yaml`

```yaml
clawcloud:
  # 基础信息
  name: "ClawCloud"
  enabled: true
  login_url: "https://eu-central-1.run.claw.cloud/signin"

  # 成功标识（支持反向匹配 !）
  success_url_patterns:
    - "claw.cloud"
    - "!signin"

  # OAuth 按钮选择器（优先级顺序）
  oauth_button_selectors:
    - 'button:has-text("GitHub")'
    - '[data-provider="github"]'

  # 2FA 配置
  two_factor:
    strategy: "auto"  # auto: 自动检测 | mobile | totp
    mobile_wait: 120  # GitHub Mobile 等待秒数
    totp_wait: 120    # TOTP 输入等待秒数

  # 设备验证配置
  device_verification:
    wait: 30  # 设备验证等待秒数

  # 超时配置
  timeouts:
    page_load: 30
    oauth_callback: 60
    network_idle: 15

  # 保活 URLs（登录后访问）
  keepalive_urls:
    - url: "/"
      name: "控制台"
    - url: "/apps"
      name: "应用列表"

  # Cookie 配置
  cookie_domain: "github.com"
  cookie_names:
    - "user_session"

  # Cookie 存储目标
  cookie_targets:
    - type: "github_secret"
      secret_name: "GH_SESSION"
    - type: "file"
      path: "./cookies/clawcloud.json"
```

## 开发指南

### 添加新站点（配置驱动）

大多数站点只需在 `config/sites.yaml` 添加配置：

```yaml
vercel:
  name: "Vercel"
  enabled: true
  login_url: "https://vercel.com/login"
  oauth_button_selectors:
    - 'button[data-testid="login-with-github"]'
  success_url_patterns:
    - "vercel.com/dashboard"
  # ... 其他配置同上
```

### 添加自定义站点适配器

如果站点有特殊逻辑，创建 `sites/your_site.py`：

```python
from sites.base import SiteAdapter

class YourSiteAdapter(SiteAdapter):
    def _check_already_logged_in(self, page) -> bool:
        # 自定义登录检测
        try:
            page.locator('.user-avatar').wait_for(timeout=5000)
            return True
        except:
            return False

    def _do_post_login(self, page):
        # 自定义登录后操作
        super()._do_post_login(page)
        # 额外操作...
```

### 添加新通知渠道

实现 `NotifierInterface`：

```python
from core.types import NotifierInterface

class EmailNotifier(NotifierInterface):
    def notify(self, message: str, level: str = "INFO", attachments=None):
        # 发送邮件实现
        pass

    def wait_user_input(self, prompt: str, pattern: str, timeout: int):
        # 邮件中接收验证码实现
        pass

    def send_photo(self, path: str, caption: str = ""):
        # 发送附件实现
        pass
```

## 部署说明

### GitHub Actions

**Secrets 配置**（在仓库 Settings -> Secrets 设置）：

| Secret | 说明 | 必需 |
|--------|------|------|
| `GH_USERNAME` | GitHub 用户名 | ✅ |
| `GH_PASSWORD` | GitHub 密码 | ✅ |
| `GH_SESSION` | GitHub Session Cookie | ⚪ 可选 |
| `TG_BOT_TOKEN` | Telegram Bot Token | ⚪ 可选 |
| `TG_CHAT_ID` | Telegram Chat ID | ⚪ 可选 |
| `REPO_TOKEN` | GitHub PAT (自动更新 Secret) | ⚪ 可选 |

**优化措施**：
- ✅ Pip 依赖缓存（`cache: 'pip'`）
- ✅ Playwright 浏览器缓存（`~/.cache/ms-playwright`）
- ✅ 失败时自动上传截图为 Artifact

### 本地运行

```bash
export GH_USERNAME="your_username"
export GH_PASSWORD="your_password"
export TG_BOT_TOKEN="your_token"  # 可选
export TG_CHAT_ID="your_chat_id"  # 可选

python main.py clawcloud
```

## 故障排查

### 常见问题

1. **设备验证超时**
   - 检查邮箱是否收到验证邮件
   - 在 GitHub App 中批准登录
   - 增加 `device_verification.wait` 参数

2. **双因素认证失败**
   - 确保 Telegram Bot 配置正确
   - 检查验证码格式：`/code 123456`
   - 查看 Telegram 截图确认页面状态

3. **OAuth 回调超时**
   - 检查 `success_url_patterns` 是否匹配
   - 增加 `timeouts.oauth_callback` 参数
   - 查看截图确认页面实际 URL

### 调试技巧

1. **本地运行查看详细日志**：
   ```bash
   python main.py clawcloud
   ```

2. **查看 GitHub Actions 截图**：
   - 失败时自动上传到 Artifacts
   - 点击 Actions 页面 -> 失败的 Run -> Artifacts

3. **Telegram 实时反馈**：
   - 配置 Telegram 后可接收实时截图
   - 可交互式输入验证码

## 技术栈

- **Python 3.11+**
- **Playwright**：浏览器自动化
- **PyYAML**：配置文件解析
- **PyNaCl**：Secret 加密
- **Requests**：HTTP 请求（Telegram API）

## 代码风格

遵循项目根目录 `CLAUDE.md` 中的全局规范：

- ✅ 类型注解：使用 `dataclass` + Type Hints
- ✅ 精简高效：无冗余代码
- ✅ 文档最小化：代码自解释，非必要不注释
- ✅ 仅针对性改动：不影响现有功能

## 未来扩展

1. **更多站点支持**：Railway、Render、Fly.io 等
2. **更多通知渠道**：Email、Slack、Discord
3. **Cookie 加密存储**：实现文件加密功能
4. **Web UI**：可视化配置和监控界面
5. **Docker 镜像**：容器化部署
