"""
输入校验模块

提供6位数字和密钥的格式校验功能。
"""

import re
from typing import Union

from .exceptions import InvalidInputError, InvalidKeyError

# 6位数字正则模式
SIX_DIGIT_PATTERN = re.compile(r"^\d{6}$")

# 常量定义
KEY_LEN = 32  # AES-256 需要32字节密钥
IV_LEN = 12  # GCM模式推荐IV长度
TAG_LEN = 16  # GCM认证标签长度
MIN_CIPHERTEXT_LEN = IV_LEN + TAG_LEN  # 最小密文长度（空明文）= 28字节
MIN_PLAINTEXT_LEN = 6  # 最小明文长度（6位数字）
MIN_SERIALIZED_LEN = IV_LEN + MIN_PLAINTEXT_LEN + TAG_LEN  # 最小序列化长度 = 34字节


def validate_six_digit(value: str) -> None:
    """
    校验输入是否为有效的6位纯数字。

    Args:
        value: 待校验的字符串

    Raises:
        InvalidInputError: 输入非6位纯数字
    """
    if value is None:
        raise InvalidInputError("Input cannot be None")

    if not isinstance(value, str):
        raise InvalidInputError(f"Input must be string, got {type(value).__name__}")

    if not SIX_DIGIT_PATTERN.match(value):
        raise InvalidInputError(
            f"Input must be exactly 6 digits, got: '{value}' (length={len(value)})"
        )


def is_valid_six_digit(value: str) -> bool:
    """
    检查输入是否为有效的6位纯数字（不抛异常）。

    Args:
        value: 待检查的字符串

    Returns:
        True 如果有效，False 如果无效
    """
    try:
        validate_six_digit(value)
        return True
    except InvalidInputError:
        return False


def validate_key(key: bytes) -> None:
    """
    校验密钥长度是否为32字节。

    Args:
        key: 密钥字节

    Raises:
        InvalidKeyError: 密钥长度不是32字节
    """
    if key is None:
        raise InvalidKeyError("Key cannot be None")

    if not isinstance(key, bytes):
        raise InvalidKeyError(f"Key must be bytes, got {type(key).__name__}")

    if len(key) != KEY_LEN:
        raise InvalidKeyError(
            f"Key must be {KEY_LEN} bytes (256 bits), got {len(key)} bytes"
        )


def validate_ciphertext(data: bytes) -> None:
    """
    校验密文数据格式（解密后Base64解码的原始字节）。

    最小有效密文长度 = IV(12) + 明文(6) + Tag(16) = 34 字节

    Args:
        data: Base64解码后的密文数据

    Raises:
        InvalidInputError: 密文长度不足
    """
    if data is None:
        raise InvalidInputError("Ciphertext data cannot be None")

    if not isinstance(data, bytes):
        raise InvalidInputError(
            f"Ciphertext must be bytes, got {type(data).__name__}"
        )

    if len(data) < MIN_SERIALIZED_LEN:
        raise InvalidInputError(
            f"Ciphertext too short: {len(data)} bytes, "
            f"minimum is {MIN_SERIALIZED_LEN} bytes"
        )