# GitHub OAuth 自动登录框架

[![GitHub](https://img.shields.io/badge/GitHub-h7ml%2Fgithub--oauth--autologin-blue?logo=github)](https://github.com/h7ml/github-oauth-autologin)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

通用的 GitHub OAuth 自动登录工具，支持多站点配置，完善的 2FA 处理，Telegram 实时通知。

> **💡 项目灵感**：本项目思路来自 [oyz8/ClawCloud-Run](https://github.com/oyz8/ClawCloud-Run)，在其基础上进行了通用化改造和功能增强。

---

## 📑 目录

- [特性](#-特性)
- [安装](#-安装)
- [配置](#️-配置)
- [使用](#-使用)
- [添加新站点](#-添加新站点)
- [项目结构](#-项目结构)
- [安全说明](#-安全说明)
- [贡献](#-贡献)
- [常见问题](#-常见问题)
- [License](#-license)

---

## ✨ 特性

- 🔧 **配置驱动**：通过 YAML 配置支持任意使用 GitHub OAuth 的站点
- 🔐 **完善的 2FA 处理**：自动处理设备验证、GitHub Mobile、TOTP 验证码
- 📱 **Telegram 集成**：实时通知 + 双向通信（接收验证码）
- 🍪 **智能 Cookie 管理**：自动提取并更新到 GitHub Secrets/文件
- 🎯 **插件化架构**：核心模块独立，易于扩展新站点
- 🚀 **CI/CD 支持**：GitHub Actions 自动化运行

## 📦 安装

```bash
# 克隆仓库
git clone https://github.com/h7ml/github-oauth-autologin.git
cd github-oauth-autologin

# 安装依赖
pip install -r requirements.txt
playwright install chromium
```

## ⚙️ 配置

### 1. 站点配置 (`config/sites.yaml`)

```yaml
clawcloud:
  name: "ClawCloud"
  enabled: true
  login_url: "https://eu-central-1.run.claw.cloud/signin"

  oauth_button_selectors:
    - 'button:has-text("GitHub")'

  success_url_patterns:
    - "claw.cloud"
    - "!signin"  # 不包含 signin

  two_factor:
    strategy: "auto"  # auto | mobile | totp
    mobile_wait: 120
    totp_wait: 120

  cookie_targets:
    - type: "github_secret"
      secret_name: "GH_SESSION"
```

### 2. 凭据配置（环境变量）

```bash
export GH_USERNAME="your_username"
export GH_PASSWORD="your_password"
export GH_SESSION="your_session_cookie"  # 可选

# Telegram 通知（可选）
export TG_BOT_TOKEN="your_bot_token"
export TG_CHAT_ID="your_chat_id"

# GitHub Actions Secret 更新（可选）
export REPO_TOKEN="your_github_token"
export GITHUB_REPOSITORY="owner/repo"
```

## 🚀 使用

### 本地运行

```bash
# 登录 ClawCloud
python main.py clawcloud

# 添加新站点后
python main.py vercel
```

### GitHub Actions - 完整工作流

已配置自动化工作流（`.github/workflows/keep-alive.yml`）：

- **定时运行**：每 5 天 UTC 7:00 自动执行
- **手动触发**：在 Actions 页面点击 "Run workflow"

### 作为可复用 Action（推荐）

如果你只需要 GitHub 登录功能（含 2FA），然后自己授权其他站点：

```yaml
name: 我的自定义授权流程

on: [push]

jobs:
  authorize-sites:
    runs-on: ubuntu-latest
    steps:
      # 第一步：使用本 Action 登录 GitHub
      - name: 登录 GitHub
        id: gh-login
        uses: h7ml/github-oauth-autologin@v1
        with:
          username: ${{ secrets.GH_USERNAME }}
          password: ${{ secrets.GH_PASSWORD }}
          session_cookie: ${{ secrets.GH_SESSION }}  # 可选，复用已有 Cookie
          tg_bot_token: ${{ secrets.TG_BOT_TOKEN }}  # 可选，2FA 用
          tg_chat_id: ${{ secrets.TG_CHAT_ID }}      # 可选，2FA 用
          repo_token: ${{ secrets.REPO_TOKEN }}      # 可选，自动更新 Secret
          repository: ${{ github.repository }}       # 可选，自动更新 Secret

      # 第二步：使用登录后的 Cookie 授权你的站点
      - name: 授权 Vercel
        uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: |
          pip install playwright
          playwright install chromium
          python my_vercel_oauth.py
        env:
          GH_SESSION: ${{ steps.gh-login.outputs.gh_session }}

      - name: 授权 Railway
        run: python my_railway_oauth.py
        env:
          GH_SESSION: ${{ steps.gh-login.outputs.gh_session }}
```

**持久化配置（强烈推荐）**：

✅ **为什么要持久化**：
- GitHub Session Cookie 有效期长（几个月到一年）
- 避免每次都触发 2FA（提高效率）
- 自动更新 Secret，形成闭环

🔧 **如何配置**：
1. 创建 GitHub PAT：Settings -> Developer settings -> Personal access tokens -> Fine-grained tokens
   - 权限：`Secrets: Read and write`
   - Repository access: 选择你的仓库
2. 添加到仓库 Secrets：`REPO_TOKEN`
3. 在 Action 中传入 `repo_token` 和 `repository` 参数（见上面示例）

**首次运行**：需要 2FA 验证，登录成功后自动更新 `GH_SESSION` Secret
**后续运行**：直接使用缓存的 Cookie，无需 2FA（除非 Cookie 失效）

**你的 Python 脚本示例** (`my_vercel_oauth.py`):

```python
import os
from playwright.sync_api import sync_playwright

gh_session = os.getenv("GH_SESSION")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()

    # 注入 GitHub Cookie
    context.add_cookies([{
        'name': 'user_session',
        'value': gh_session,
        'domain': '.github.com',
        'path': '/'
    }])

    page = context.new_page()

    # 你的授权逻辑
    page.goto("https://vercel.com/login")
    page.click('button:has-text("Continue with GitHub")')
    page.wait_for_url("**/dashboard")

    print("✅ Vercel 授权成功")
    browser.close()
```

**Action 输出**：
- `gh_session`: GitHub Session Cookie (user_session)
- `login_status`: 登录状态 (success/failed)

## 🔧 添加新站点

### 方法 1: 配置文件（推荐）

在 `config/sites.yaml` 添加：

```yaml
your_site:
  name: "Your Site"
  enabled: true
  login_url: "https://your-site.com/login"

  oauth_button_selectors:
    - 'button:has-text("Sign in with GitHub")'

  success_url_patterns:
    - "your-site.com/dashboard"

  two_factor:
    strategy: "auto"
    mobile_wait: 120
    totp_wait: 120

  device_verification:
    wait: 30

  timeouts:
    page_load: 30
    oauth_callback: 60
    network_idle: 15

  cookie_domain: "github.com"
  cookie_names:
    - "user_session"

  cookie_targets:
    - type: "github_secret"
      secret_name: "GH_SESSION"
```

### 方法 2: 自定义适配器（高级）

如需复杂逻辑，创建 `sites/your_site.py`：

```python
from sites.base import SiteAdapter

class YourSiteAdapter(SiteAdapter):
    def _check_already_logged_in(self, page) -> bool:
        # 自定义登录检测逻辑
        return super()._check_already_logged_in(page)
```

## 📂 项目结构

```
github-oauth-autologin/
├── core/                    # 核心模块
│   ├── types.py            # 类型定义
│   ├── github_auth.py      # GitHub 认证（2FA 处理）
│   ├── oauth_handler.py    # OAuth 流程控制
│   └── cookie_manager.py   # Cookie 管理
├── notifiers/              # 通知器
│   └── telegram.py         # Telegram 实现
├── sites/                  # 站点适配器
│   ├── base.py            # 基类
│   └── clawcloud.py       # ClawCloud 示例
├── config/                 # 配置文件
│   ├── sites.yaml         # 站点配置
│   └── credentials.yaml.example
├── .github/workflows/      # GitHub Actions
│   └── keep-alive.yml     # 自动登录工作流
├── main.py                 # CLI 入口
├── requirements.txt        # 依赖清单
├── README.md              # 项目文档
├── CLAUDE.md              # 技术文档
└── .gitignore
```

## 🔐 安全说明

- ✅ 凭据通过环境变量传递，不写入代码
- ✅ Cookie 可选加密存储
- ✅ GitHub Actions Secrets 使用 NaCl 加密更新
- ✅ 支持 Headless 模式运行

## 🤝 贡献

欢迎提交 PR 添加新站点支持！只需在 `config/sites.yaml` 添加配置即可。

### 参与贡献

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/your-site`)
3. 提交更改 (`git commit -m 'Add support for YourSite'`)
4. 推送到分支 (`git push origin feature/your-site`)
5. 提交 Pull Request

## 👨‍💻 作者

**h7ml**
- GitHub: [@h7ml](https://github.com/h7ml)
- Email: h7ml@qq.com

## 📧 联系方式

- 💬 提交 [Issue](https://github.com/h7ml/github-oauth-autologin/issues)
- 📧 邮件: h7ml@qq.com

## 📝 常见问题

### Q: 如何获取 Telegram Bot Token？

1. 与 [@BotFather](https://t.me/BotFather) 对话创建 Bot
2. 获取 Token 并设置到 `TG_BOT_TOKEN`
3. 向你的 Bot 发送消息，访问 `https://api.telegram.org/bot<TOKEN>/getUpdates` 获取 `chat_id`

### Q: 双因素认证怎么处理？

- **GitHub Mobile**：脚本会截图并通过 Telegram 发送数字，在手机 App 确认即可
- **TOTP 验证码**：在 Telegram 发送 `/code 123456` 格式消息

### Q: 如何调试登录失败？

1. 查看 GitHub Actions 日志
2. 检查 Telegram 收到的截图
3. 本地运行查看详细输出：`python main.py clawcloud`

## 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件

---

<div align="center">

**如果这个项目对你有帮助，请给它一个 ⭐️ Star！**

Made with ❤️ by [h7ml](https://github.com/h7ml)

</div>
