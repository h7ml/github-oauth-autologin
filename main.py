#!/usr/bin/env python3
"""通用 GitHub OAuth 自动登录工具"""
import os
import sys
import yaml
from playwright.sync_api import sync_playwright
from core.types import GitHubCredentials, SiteConfig, TwoFactorConfig, DeviceVerificationConfig, TimeoutConfig, KeepAliveURL, CookieTarget
from notifiers.telegram import TelegramNotifier
from sites.clawcloud import ClawCloudAdapter


def load_config(site_name: str) -> SiteConfig:
    """加载站点配置"""
    with open('config/sites.yaml', 'r') as f:
        config_data = yaml.safe_load(f)

    site_data = config_data.get(site_name)
    if not site_data:
        raise ValueError(f"站点 '{site_name}' 未配置")

    if not site_data.get('enabled', True):
        raise ValueError(f"站点 '{site_name}' 已禁用")

    return SiteConfig(
        name=site_data['name'],
        enabled=site_data['enabled'],
        login_url=site_data['login_url'],
        success_url_patterns=site_data['success_url_patterns'],
        oauth_button_selectors=site_data['oauth_button_selectors'],
        two_factor=TwoFactorConfig(
            strategy=site_data['two_factor']['strategy'],
            mobile_wait=site_data['two_factor']['mobile_wait'],
            totp_wait=site_data['two_factor']['totp_wait']
        ),
        device_verification=DeviceVerificationConfig(
            wait=site_data['device_verification']['wait']
        ),
        timeouts=TimeoutConfig(
            page_load=site_data['timeouts']['page_load'],
            oauth_callback=site_data['timeouts']['oauth_callback'],
            network_idle=site_data['timeouts']['network_idle']
        ),
        keepalive_urls=[
            KeepAliveURL(url=item['url'], name=item['name'])
            for item in site_data.get('keepalive_urls', [])
        ],
        cookie_domain=site_data.get('cookie_domain', 'github.com'),
        cookie_names=site_data.get('cookie_names', ['user_session']),
        cookie_targets=[
            CookieTarget(
                type=target['type'],
                secret_name=target.get('secret_name'),
                path=target.get('path'),
                encrypt=target.get('encrypt', False)
            )
            for target in site_data.get('cookie_targets', [])
        ]
    )


def load_credentials() -> GitHubCredentials:
    """加载凭据"""
    return GitHubCredentials(
        username=os.environ.get('GH_USERNAME', ''),
        password=os.environ.get('GH_PASSWORD', ''),
        session_cookie=os.environ.get('GH_SESSION', '').strip()
    )


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python main.py <site_name>")
        print("示例: python main.py clawcloud")
        sys.exit(1)

    site_name = sys.argv[1]

    try:
        # 加载配置
        config = load_config(site_name)
        credentials = load_credentials()
        notifier = TelegramNotifier()

        if not credentials.username or not credentials.password:
            print("❌ 缺少 GitHub 凭据")
            print("请设置环境变量: GH_USERNAME, GH_PASSWORD")
            sys.exit(1)

        # 创建适配器
        adapter = ClawCloudAdapter(config, credentials, notifier)

        # 运行登录
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox']
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()

            try:
                success = adapter.run(context, page)
                sys.exit(0 if success else 1)
            finally:
                browser.close()

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
