"""
Six Digit Crypto - 安全的6位数字加密模块

使用 AES-256-GCM 算法对6位数字（如验证码、PIN码）进行安全加解密。

Example:
    >>> from six_digit_crypto import encrypt, decrypt, generate_key
    >>>
    >>> # 生成密钥
    >>> key = generate_key()
    >>>
    >>> # 加密
    >>> cipher = encrypt("123456", key)
    >>>
    >>> # 解密
    >>> original = decrypt(cipher, key)
    >>> original
    '123456'
"""

from .core import decrypt, encrypt, generate_key
from .exceptions import (
    DecryptionError,
    InvalidInputError,
    InvalidKeyError,
    SixDigitCryptoError,
)

__version__ = "1.0.0"

__all__ = [
    # 核心函数
    "encrypt",
    "decrypt",
    "generate_key",
    # 异常类
    "SixDigitCryptoError",
    "InvalidInputError",
    "InvalidKeyError",
    "DecryptionError",
]