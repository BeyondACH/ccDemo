"""
核心加密/解密模块

使用 AES-256-GCM 算法实现6位数字的安全加解密。
"""

import base64
import secrets
from typing import Union

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .exceptions import DecryptionError, InvalidInputError, InvalidKeyError
from .validation import (
    IV_LEN,
    KEY_LEN,
    TAG_LEN,
    validate_ciphertext,
    validate_key,
    validate_six_digit,
)


def _normalize_key(key: Union[str, bytes]) -> bytes:
    """
    标准化密钥为32字节。

    Args:
        key: 32字节密钥（bytes）或 Base64 编码的密钥字符串

    Returns:
        32字节密钥

    Raises:
        InvalidKeyError: 密钥格式无效或长度错误
    """
    if isinstance(key, bytes):
        validate_key(key)
        return key

    if isinstance(key, str):
        try:
            decoded = base64.b64decode(key, validate=True)
            validate_key(decoded)
            return decoded
        except Exception as e:
            raise InvalidKeyError(
                f"Failed to decode Base64 key: {e}"
            ) from e

    raise InvalidKeyError(
        f"Key must be bytes or Base64 string, got {type(key).__name__}"
    )


def _serialize(iv: bytes, ciphertext: bytes, tag: bytes) -> bytes:
    """
    序列化加密结果：IV || ciphertext || tag

    拼接顺序说明：
    - IV: 12字节，放在最前面便于提取
    - ciphertext: 可变长度（加密后的明文）
    - tag: 16字节认证标签，放在最后
    """
    return iv + ciphertext + tag


def _deserialize(data: bytes) -> tuple[bytes, bytes, bytes]:
    """
    反序列化加密数据。

    Args:
        data: 序列化的加密数据（IV || ciphertext || tag）

    Returns:
        (iv, ciphertext, tag) 元组

    Raises:
        InvalidInputError: 数据格式无效
    """
    validate_ciphertext(data)

    iv = data[:IV_LEN]
    tag = data[-TAG_LEN:]
    ciphertext = data[IV_LEN:-TAG_LEN]

    return iv, ciphertext, tag


def generate_key() -> str:
    """
    生成安全的32字节密钥，返回Base64编码字符串。

    Returns:
        Base64编码的密钥字符串（44字符）

    Example:
        >>> key = generate_key()
        >>> cipher = encrypt("123456", key)
        >>> original = decrypt(cipher, key)
        >>> original
        '123456'
    """
    raw_key = secrets.token_bytes(KEY_LEN)
    return base64.b64encode(raw_key).decode("utf-8")


def encrypt(six_digit: str, key: Union[str, bytes]) -> str:
    """
    加密6位数字。

    使用 AES-256-GCM 算法进行认证加密，确保机密性和完整性。

    Args:
        six_digit: 6位纯数字字符串，如 "123456"
        key: 32字节密钥（bytes）或 Base64 编码的密钥字符串

    Returns:
        Base64 编码的加密字符串（约44字符）

    Raises:
        InvalidInputError: 输入非6位纯数字
        InvalidKeyError: 密钥格式无效

    Example:
        >>> key = generate_key()
        >>> encrypt("123456", key)  # doctest: +SKIP
        'YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXowMTIzNDU2...'
    """
    # 1. 校验输入
    validate_six_digit(six_digit)

    # 2. 标准化密钥
    normalized_key = _normalize_key(key)

    # 3. 生成随机IV（12字节，GCM推荐长度）
    iv = secrets.token_bytes(IV_LEN)

    # 4. AES-GCM 加密
    aesgcm = AESGCM(normalized_key)
    plaintext = six_digit.encode("utf-8")

    # cryptography 库的 encrypt 返回 ciphertext + tag
    ciphertext_with_tag = aesgcm.encrypt(iv, plaintext, None)

    # 5. 分离 ciphertext 和 tag（tag 固定16字节）
    ciphertext = ciphertext_with_tag[:-TAG_LEN]
    tag = ciphertext_with_tag[-TAG_LEN:]

    # 6. 序列化并 Base64 编码
    serialized = _serialize(iv, ciphertext, tag)

    return base64.b64encode(serialized).decode("utf-8")


def decrypt(ciphertext: str, key: Union[str, bytes]) -> str:
    """
    解密还原6位数字。

    Args:
        ciphertext: encrypt() 返回的加密字符串
        key: 32字节密钥（bytes）或 Base64 编码的密钥字符串

    Returns:
        原始6位数字字符串

    Raises:
        InvalidInputError: 加密字符串格式无效
        InvalidKeyError: 密钥格式无效
        DecryptionError: 解密失败（密钥错误或数据被篡改）

    Example:
        >>> key = generate_key()
        >>> cipher = encrypt("123456", key)
        >>> decrypt(cipher, key)
        '123456'
    """
    # 1. Base64 解码
    try:
        decoded = base64.b64decode(ciphertext, validate=True)
    except Exception as e:
        raise InvalidInputError(
            f"Invalid Base64 ciphertext: {e}"
        ) from e

    # 2. 反序列化
    iv, ct, tag = _deserialize(decoded)

    # 3. 标准化密钥
    normalized_key = _normalize_key(key)

    # 4. AES-GCM 解密
    try:
        aesgcm = AESGCM(normalized_key)
        # cryptography 库期望 ciphertext + tag 的形式
        ciphertext_with_tag = ct + tag
        plaintext = aesgcm.decrypt(iv, ciphertext_with_tag, None)
    except Exception as e:
        raise DecryptionError(
            f"Decryption failed (wrong key or tampered data): {e}"
        ) from e

    # 5. 解码明文
    try:
        result = plaintext.decode("utf-8")
    except UnicodeDecodeError as e:
        raise DecryptionError(
            f"Decrypted data is not valid UTF-8: {e}"
        ) from e

    # 6. 校验结果为6位数字（确保完整性）
    try:
        validate_six_digit(result)
    except InvalidInputError as e:
        raise DecryptionError(
            f"Decrypted value is not valid 6-digit: {e}"
        ) from e

    return result