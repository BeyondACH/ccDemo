"""
Six Digit Crypto 单元测试

覆盖场景：
- 正常加解密流程
- 边界值测试
- 输入格式错误
- 密钥格式错误
- 解密失败场景
- 密钥格式兼容性
"""

import base64
import secrets
import unittest

from six_digit_crypto import (
    DecryptionError,
    InvalidInputError,
    InvalidKeyError,
    SixDigitCryptoError,
    decrypt,
    encrypt,
    generate_key,
)
from six_digit_crypto.validation import (
    is_valid_six_digit,
    validate_ciphertext,
    validate_key,
    validate_six_digit,
)


class TestGenerateKey(unittest.TestCase):
    """密钥生成测试"""

    def test_generate_key_returns_string(self):
        """生成的密钥应为字符串"""
        key = generate_key()
        self.assertIsInstance(key, str)

    def test_generate_key_length(self):
        """Base64编码的32字节密钥应为44字符"""
        key = generate_key()
        self.assertEqual(len(key), 44)

    def test_generate_key_valid_base64(self):
        """密钥应为有效Base64字符串"""
        key = generate_key()
        decoded = base64.b64decode(key)
        self.assertEqual(len(decoded), 32)

    def test_generate_key_uniqueness(self):
        """每次生成的密钥应不同"""
        key1 = generate_key()
        key2 = generate_key()
        self.assertNotEqual(key1, key2)


class TestEncrypt(unittest.TestCase):
    """加密功能测试"""

    def setUp(self):
        """测试前置准备"""
        self.key = generate_key()
        self.key_bytes = base64.b64decode(self.key)

    def test_encrypt_returns_string(self):
        """加密结果应为字符串"""
        result = encrypt("123456", self.key)
        self.assertIsInstance(result, str)

    def test_encrypt_output_not_plaintext(self):
        """加密结果不应包含明文"""
        result = encrypt("123456", self.key)
        self.assertNotIn("123456", result)

    def test_encrypt_produces_different_ciphertext(self):
        """相同输入应产生不同密文（因为随机IV）"""
        cipher1 = encrypt("123456", self.key)
        cipher2 = encrypt("123456", self.key)
        self.assertNotEqual(cipher1, cipher2)

    def test_encrypt_with_bytes_key(self):
        """应支持bytes格式密钥"""
        result = encrypt("123456", self.key_bytes)
        self.assertIsInstance(result, str)

    def test_encrypt_boundary_000000(self):
        """边界值测试：000000"""
        result = encrypt("000000", self.key)
        self.assertIsInstance(result, str)

    def test_encrypt_boundary_999999(self):
        """边界值测试：999999"""
        result = encrypt("999999", self.key)
        self.assertIsInstance(result, str)

    def test_encrypt_with_leading_zeros(self):
        """前导零数字应正确处理"""
        original = "001234"
        cipher = encrypt(original, self.key)
        decrypted = decrypt(cipher, self.key)
        self.assertEqual(decrypted, original)

    def test_encrypt_invalid_input_none(self):
        """无效输入：None"""
        with self.assertRaises(InvalidInputError):
            encrypt(None, self.key)  # type: ignore

    def test_encrypt_invalid_input_empty(self):
        """无效输入：空字符串"""
        with self.assertRaises(InvalidInputError):
            encrypt("", self.key)

    def test_encrypt_invalid_input_too_short(self):
        """无效输入：少于6位"""
        with self.assertRaises(InvalidInputError):
            encrypt("12345", self.key)

    def test_encrypt_invalid_input_too_long(self):
        """无效输入：多于6位"""
        with self.assertRaises(InvalidInputError):
            encrypt("1234567", self.key)

    def test_encrypt_invalid_input_letters(self):
        """无效输入：包含字母"""
        with self.assertRaises(InvalidInputError):
            encrypt("abc123", self.key)

    def test_encrypt_invalid_input_special_chars(self):
        """无效输入：包含特殊字符"""
        with self.assertRaises(InvalidInputError):
            encrypt("12345!", self.key)

    def test_encrypt_invalid_key_short(self):
        """无效密钥：长度不足"""
        short_key = secrets.token_bytes(16)
        with self.assertRaises(InvalidKeyError):
            encrypt("123456", short_key)

    def test_encrypt_invalid_key_long(self):
        """无效密钥：长度过长"""
        long_key = secrets.token_bytes(64)
        with self.assertRaises(InvalidKeyError):
            encrypt("123456", long_key)

    def test_encrypt_invalid_key_base64(self):
        """无效密钥：无效Base64"""
        with self.assertRaises(InvalidKeyError):
            encrypt("123456", "not-valid-base64!!!")


class TestDecrypt(unittest.TestCase):
    """解密功能测试"""

    def setUp(self):
        """测试前置准备"""
        self.key = generate_key()
        self.key_bytes = base64.b64decode(self.key)

    def test_decrypt_returns_original(self):
        """解密应还原原始数据"""
        original = "123456"
        cipher = encrypt(original, self.key)
        result = decrypt(cipher, self.key)
        self.assertEqual(result, original)

    def test_decrypt_with_bytes_key(self):
        """解密应支持bytes格式密钥"""
        original = "654321"
        cipher = encrypt(original, self.key)
        result = decrypt(cipher, self.key_bytes)
        self.assertEqual(result, original)

    def test_decrypt_boundary_000000(self):
        """边界值测试：000000"""
        original = "000000"
        cipher = encrypt(original, self.key)
        result = decrypt(cipher, self.key)
        self.assertEqual(result, original)

    def test_decrypt_boundary_999999(self):
        """边界值测试：999999"""
        original = "999999"
        cipher = encrypt(original, self.key)
        result = decrypt(cipher, self.key)
        self.assertEqual(result, original)

    def test_decrypt_wrong_key(self):
        """错误密钥解密应失败"""
        cipher = encrypt("123456", self.key)
        wrong_key = generate_key()
        with self.assertRaises(DecryptionError):
            decrypt(cipher, wrong_key)

    def test_decrypt_invalid_base64(self):
        """无效Base64密文应失败"""
        with self.assertRaises(InvalidInputError):
            decrypt("not-valid-base64!!!", self.key)

    def test_decrypt_tampered_ciphertext(self):
        """篡改密文应导致解密失败"""
        original = "123456"
        cipher = encrypt(original, self.key)
        # 篡改密文的中间部分
        tampered = cipher[:10] + ("A" if cipher[10] != "A" else "B") + cipher[11:]
        with self.assertRaises(DecryptionError):
            decrypt(tampered, self.key)

    def test_decrypt_tampered_iv(self):
        """篡改IV应导致解密失败"""
        original = "123456"
        cipher = encrypt(original, self.key)
        decoded = list(base64.b64decode(cipher))
        # 篡改第一个字节（IV的一部分）
        decoded[0] = (decoded[0] + 1) % 256
        tampered = base64.b64encode(bytes(decoded)).decode()
        with self.assertRaises(DecryptionError):
            decrypt(tampered, self.key)

    def test_decrypt_too_short(self):
        """过短密文应失败"""
        short_cipher = base64.b64encode(b"short").decode()
        with self.assertRaises(InvalidInputError):
            decrypt(short_cipher, self.key)


class TestValidation(unittest.TestCase):
    """校验模块测试"""

    def test_validate_six_digit_valid(self):
        """有效6位数字"""
        # 不应抛出异常
        validate_six_digit("123456")
        validate_six_digit("000000")
        validate_six_digit("999999")

    def test_validate_six_digit_invalid(self):
        """无效输入应抛出异常"""
        with self.assertRaises(InvalidInputError):
            validate_six_digit("12345")
        with self.assertRaises(InvalidInputError):
            validate_six_digit("1234567")
        with self.assertRaises(InvalidInputError):
            validate_six_digit("abcdef")
        with self.assertRaises(InvalidInputError):
            validate_six_digit("12345a")

    def test_is_valid_six_digit(self):
        """非异常式校验函数"""
        self.assertTrue(is_valid_six_digit("123456"))
        self.assertTrue(is_valid_six_digit("000000"))
        self.assertFalse(is_valid_six_digit("12345"))
        self.assertFalse(is_valid_six_digit("abcdef"))

    def test_validate_key_valid(self):
        """有效密钥"""
        key = secrets.token_bytes(32)
        # 不应抛出异常
        validate_key(key)

    def test_validate_key_invalid_length(self):
        """无效密钥长度"""
        with self.assertRaises(InvalidKeyError):
            validate_key(secrets.token_bytes(16))
        with self.assertRaises(InvalidKeyError):
            validate_key(secrets.token_bytes(64))

    def test_validate_ciphertext_valid(self):
        """有效密文长度"""
        # 最小有效长度 = 12(IV) + 6(明文) + 16(Tag) = 34
        valid_data = secrets.token_bytes(34)
        validate_ciphertext(valid_data)
        # 更长的数据也应有效
        validate_ciphertext(secrets.token_bytes(100))

    def test_validate_ciphertext_too_short(self):
        """密文过短"""
        with self.assertRaises(InvalidInputError):
            validate_ciphertext(secrets.token_bytes(33))


class TestExceptions(unittest.TestCase):
    """异常类测试"""

    def test_exception_hierarchy(self):
        """异常继承关系"""
        self.assertTrue(issubclass(InvalidInputError, SixDigitCryptoError))
        self.assertTrue(issubclass(InvalidKeyError, SixDigitCryptoError))
        self.assertTrue(issubclass(DecryptionError, SixDigitCryptoError))
        self.assertTrue(issubclass(SixDigitCryptoError, Exception))

    def test_exception_message(self):
        """异常消息"""
        exc = InvalidInputError("Test message")
        self.assertEqual(str(exc), "Test message")
        self.assertEqual(exc.message, "Test message")

    def test_exception_repr(self):
        """异常repr"""
        exc = InvalidInputError("Test message")
        self.assertIn("InvalidInputError", repr(exc))


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_full_cycle_multiple_values(self):
        """完整加解密周期（多个值）"""
        key = generate_key()
        test_values = ["123456", "000000", "999999", "555555", "111222"]

        for value in test_values:
            with self.subTest(value=value):
                cipher = encrypt(value, key)
                result = decrypt(cipher, key)
                self.assertEqual(result, value)

    def test_cross_key_isolation(self):
        """不同密钥隔离测试"""
        key1 = generate_key()
        key2 = generate_key()

        cipher1 = encrypt("123456", key1)
        cipher2 = encrypt("123456", key2)

        # 使用错误密钥无法解密
        with self.assertRaises(DecryptionError):
            decrypt(cipher1, key2)
        with self.assertRaises(DecryptionError):
            decrypt(cipher2, key1)


if __name__ == "__main__":
    unittest.main()