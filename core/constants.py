"""常量定义"""


class Timeouts:
    """超时配置（毫秒）"""

    PAGE_LOAD = 30000
    NETWORK_IDLE = 30000
    LOGIN_SLEEP = 3000
    AUTHORIZATION_SLEEP = 3000
    OAUTH_CALLBACK = 60000
    DEVICE_VERIFICATION = 30
    TWO_FACTOR_MOBILE = 120
    TWO_FACTOR_TOTP = 120
    ELEMENT_VISIBLE = 5000
    SHORT_WAIT = 2000
    API_REQUEST = 30


class RetryConfig:
    """重试配置"""

    MAX_ATTEMPTS = 3
    INITIAL_DELAY = 1.0
    BACKOFF_FACTOR = 2.0
    TELEGRAM_RETRY = 3
    GITHUB_API_RETRY = 3


class CookieConfig:
    """Cookie 配置"""

    GITHUB_DOMAIN = ".github.com"
    SESSION_COOKIE_NAME = "user_session"
    LOGGED_IN_COOKIE_NAME = "logged_in"
    LOGGED_IN_VALUE = "yes"


class GitHubUrls:
    """GitHub URL 模式"""

    LOGIN = "https://github.com/login"
    SESSION = "github.com/session"
    OAUTH_AUTHORIZE = "github.com/login/oauth/authorize"
    TWO_FACTOR = "github.com/sessions/two-factor"
    TWO_FACTOR_MOBILE = "two-factor/mobile"
    DEVICE_VERIFICATION = "verified-device"
    DEVICE_VERIFICATION_ALT = "device-verification"


class Selectors:
    """页面选择器"""

    # GitHub 登录
    LOGIN_INPUT = 'input[name="login"]'
    PASSWORD_INPUT = 'input[name="password"]'
    SUBMIT_BUTTON = 'input[type="submit"], button[type="submit"]'
    LOGGED_IN_INDICATOR = "[data-login]"
    ERROR_FLASH = ".flash-error"

    # 2FA
    TOTP_INPUT = [
        'input[autocomplete="one-time-code"]',
        'input[name="app_otp"]',
        'input[name="otp"]',
    ]

    # OAuth
    AUTHORIZE_BUTTON = [
        'button[name="authorize"]',
        'button:has-text("Authorize")',
        'button:has-text("授权")',
    ]


class Messages:
    """日志消息模板"""

    # 成功消息
    LOGIN_SUCCESS = "✅ GitHub 登录成功"
    COOKIE_EXTRACTED = "✅ 提取 Cookie: {name}"
    COOKIE_SAVED = "🔑 Cookie 已更新\n\n{secret_name} 已保存"

    # 错误消息
    LOGIN_FAILED = "❌ GitHub 登录失败"
    COOKIE_NOT_FOUND = "❌ 未找到 GitHub Session Cookie"
    CREDENTIALS_MISSING = "❌ 缺少 GitHub 凭据"

    # 警告消息
    DEVICE_VERIFICATION_NEEDED = """⚠️ 需要设备验证

请在 {wait} 秒内批准：
1️⃣ 检查邮箱点击链接
2️⃣ 或在 GitHub App 批准"""

    TWO_FACTOR_MOBILE_NEEDED = """⚠️ 需要双因素认证（GitHub Mobile）

请打开手机 GitHub App 批准本次登录。
等待时间：{timeout} 秒"""

    TWO_FACTOR_TOTP_NEEDED = """🔐 需要验证码

请在 Telegram 发送：
<code>/code 你的6位验证码</code>

等待时间：{timeout} 秒"""
