"""安全工具模块"""


def mask_sensitive(value: str, show_chars: int = 4) -> str:
    """遮蔽敏感信息

    Args:
        value: 需要遮蔽的敏感字符串
        show_chars: 头尾各显示的字符数

    Returns:
        遮蔽后的字符串

    Example:
        >>> mask_sensitive("abcdefghijklmn", 4)
        'abcd******klmn'
    """
    if not value:
        return ""

    if len(value) <= show_chars * 2:
        return "*" * len(value)

    masked_length = len(value) - show_chars * 2
    return f"{value[:show_chars]}{'*' * masked_length}{value[-show_chars:]}"


def sanitize_log_message(message: str) -> str:
    """清理日志消息中的敏感信息

    Args:
        message: 原始日志消息

    Returns:
        清理后的消息
    """
    import re

    # 遮蔽可能的 Cookie 值
    message = re.sub(
        r'(cookie["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_-]{20,})',
        lambda m: f"{m.group(1)}{mask_sensitive(m.group(2), 6)}",
        message,
        flags=re.IGNORECASE,
    )

    # 遮蔽可能的密码
    message = re.sub(
        r'(password["\']?\s*[:=]\s*["\']?)([^"\']{8,})',
        lambda m: f"{m.group(1)}{'*' * 8}",
        message,
        flags=re.IGNORECASE,
    )

    return message
