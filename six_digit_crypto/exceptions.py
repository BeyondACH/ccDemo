"""
自定义异常模块

定义 six_digit_crypto 包的异常层次结构。
"""


class SixDigitCryptoError(Exception):
    """基础异常类，所有模块异常都继承此类。"""

    def __init__(self, message: str = "Six digit crypto error"):
        self.message = message
        super().__init__(self.message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.message!r})"


class InvalidInputError(SixDigitCryptoError):
    """输入格式错误。

    当输入不符合以下要求时抛出：
    - 加密时：输入非6位纯数字
    - 解密时：密文格式无效（非Base64、长度不足等）
    """

    def __init__(self, message: str = "Invalid input format"):
        super().__init__(message)


class InvalidKeyError(SixDigitCryptoError):
    """密钥格式错误。

    当密钥不符合以下要求时抛出：
    - 长度不是32字节（256位）
    - Base64解码失败
    """

    def __init__(self, message: str = "Invalid key format"):
        super().__init__(message)


class DecryptionError(SixDigitCryptoError):
    """解密失败。

    当解密过程失败时抛出：
    - 密钥错误
    - 数据被篡改（认证标签验证失败）
    - 解密结果非6位数字
    """

    def __init__(self, message: str = "Decryption failed"):
        super().__init__(message)