# Six-Digit Crypto

安全的6位数字加密模块，使用 AES-256-GCM 算法。

## 特性

- 🔐 **AES-256-GCM** 认证加密，确保机密性和完整性
- 🔑 **安全密钥生成**，使用密码学安全随机数生成器
- ✅ **严格输入验证**，防止无效输入
- 📦 **简洁API**，开箱即用

## 安装

```bash
pip install six-digit-crypto
```

## 快速开始

```python
from six_digit_crypto import generate_key, encrypt, decrypt

# 生成密钥
key = generate_key()

# 加密6位数字
ciphertext = encrypt("123456", key)

# 解密还原
original = decrypt(ciphertext, key)
print(original)  # 输出: 123456
```

## API 文档

### `generate_key() -> str`

生成安全的32字节密钥，返回 Base64 编码字符串。

### `encrypt(six_digit: str, key: Union[str, bytes]) -> str`

加密6位数字字符串。

- **参数**：
  - `six_digit`: 6位纯数字字符串（如 "123456"）
  - `key`: 32字节密钥（bytes 或 Base64 字符串）
- **返回**：Base64 编码的加密字符串

### `decrypt(ciphertext: str, key: Union[str, bytes]) -> str`

解密还原6位数字。

- **参数**：
  - `ciphertext`: encrypt() 返回的加密字符串
  - `key`: 加密时使用的密钥
- **返回**：原始6位数字字符串

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 类型检查
mypy six_digit_crypto

# 代码格式化
ruff check six_digit_crypto
```

## 许可证

MIT License