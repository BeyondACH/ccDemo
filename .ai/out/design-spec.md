基于项目结构分析，现有仓库只有一个 `test.py` 文件（文档总结工具），与需求无关。我将以最小改动原则设计新模块。

---

## 1. 方案概述

**选型决策：AES-256-GCM**

| 评估维度 | AES-256-GCM | Fernet | FPE | 自定义XOR |
|----------|-------------|--------|-----|-----------|
| 安全性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| 依赖 | `cryptography` | `cryptography` | `ff3` 复杂 | 无 |
| 输出长度 | Base64约32字符 | Base64约100字符 | 6位数字 | 可控 |
| Python支持 | ✅ 标准实现 | ✅ | ⚠️ 需额外库 | ✅ |

**最终方案：AES-256-GCM + Base64编码**
- 安全性：业界标准，认证加密防篡改
- 输出：约32-44字符Base64字符串，适合存储/传输
- 依赖：仅需 `cryptography` 库（Python生态主流选择）

---

## 2. 架构与模块划分

```
claudeDemo/
├── six_digit_crypto/
│   ├── __init__.py          # 对外暴露接口
│   ├── core.py               # 核心加密/解密逻辑
│   ├── exceptions.py        # 自定义异常体系
│   └── validation.py        # 输入校验模块
├── tests/
│   └── test_six_digit_crypto.py  # 单元测试
└── test.py                  # (现有文件，不修改)
```

**职责边界：**

| 模块 | 职责 | 依赖 |
|------|------|------|
| `validation.py` | 输入格式校验（6位纯数字） | 无 |
| `exceptions.py` | 异常定义 | 无 |
| `core.py` | 加密/解密核心逻辑 | `cryptography`, `validation`, `exceptions` |
| `__init__.py` | 对外暴露简洁API | `core` |

---

## 3. 数据模型 / 存储设计

**不涉及持久化存储**，密钥由调用方管理。

**加密数据结构（内部）：**
```
┌─────────────┬──────────────┬────────────────┐
│  IV (12字节) │ Ciphertext   │  Auth Tag (16字节) │
└─────────────┴──────────────┴────────────────┘
       ↓ Base64编码后输出
```

**密钥要求：**
- 格式：32字节（256位）密钥
- 来源：调用方提供，建议使用 `secrets.token_bytes(32)` 生成
- 存储：**不在代码中硬编码**，通过环境变量或密钥管理服务注入

---

## 4. API / 接口 / 类设计

### 4.1 核心接口签名

```python
# six_digit_crypto/__init__.py
from .core import encrypt, decrypt
from .exceptions import (
    SixDigitCryptoError,
    InvalidInputError,
    InvalidKeyError,
    DecryptionError
)

__all__ = [
    "encrypt", "decrypt",
    "SixDigitCryptoError", "InvalidInputError", 
    "InvalidKeyError", "DecryptionError"
]
```

```python
# six_digit_crypto/core.py
from typing import Union

def encrypt(six_digit: str, key: Union[str, bytes]) -> str:
    """
    加密6位数字。
    
    Args:
        six_digit: 6位纯数字字符串，如 "123456"
        key: 32字节密钥（bytes）或 Base64 编码的密钥字符串
    
    Returns:
        Base64 编码的加密字符串（约44字符）
    
    Raises:
        InvalidInputError: 输入非6位纯数字
        InvalidKeyError: 密钥格式无效
    """
    ...

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
    """
    ...
```

### 4.2 异常体系

```python
# six_digit_crypto/exceptions.py
class SixDigitCryptoError(Exception):
    """基础异常类"""
    pass

class InvalidInputError(SixDigitCryptoError):
    """输入格式错误"""
    pass

class InvalidKeyError(SixDigitCryptoError):
    """密钥格式错误"""
    pass

class DecryptionError(SixDigitCryptoError):
    """解密失败"""
    pass
```

### 4.3 校验模块

```python
# six_digit_crypto/validation.py
import re

SIX_DIGIT_PATTERN = re.compile(r"^\d{6}$")

def validate_six_digit(value: str) -> None:
    """校验6位纯数字，失败抛出 InvalidInputError"""
    ...

def validate_key(key: bytes) -> None:
    """校验密钥长度为32字节，失败抛出 InvalidKeyError"""
    ...
```

### 4.4 辅助函数（可选，便于密钥生成）

```python
# six_digit_crypto/core.py
import secrets
import base64

def generate_key() -> str:
    """
    生成安全的32字节密钥，返回Base64编码字符串。
    
    Returns:
        Base64编码的密钥字符串（44字符）
    
    Example:
        key = generate_key()
        cipher = encrypt("123456", key)
        original = decrypt(cipher, key)
    """
    return base64.b64encode(secrets.token_bytes(32)).decode("utf-8")
```

---

## 5. 关键流程

### 5.1 加密流程

```
输入: six_digit="123456", key (Base64或bytes)
      │
      ▼
┌─────────────────────────┐
│ 1. 校验 six_digit 格式   │
│    - 非空？长度=6？     │
│    - 全部为数字？       │
└───────────┬─────────────┘
            │ 失败 → InvalidInputError
            ▼
┌─────────────────────────┐
│ 2. 标准化密钥           │
│    - bytes: 直接使用    │
│    - str: Base64解码    │
│    - 校验长度=32字节    │
└───────────┬─────────────┘
            │ 失败 → InvalidKeyError
            ▼
┌─────────────────────────┐
│ 3. 生成随机IV (12字节)  │
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ 4. AES-GCM加密          │
│    - plaintext: "123456"│
│    - key: 32字节        │
│    - iv: 12字节         │
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ 5. 拼接: IV + 密文 + Tag│
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ 6. Base64编码输出       │
└───────────┬─────────────┘
            ▼
输出: "abc...xyz" (约44字符)
```

### 5.2 解密流程

```
输入: ciphertext, key
      │
      ▼
┌─────────────────────────┐
│ 1. Base64解码           │
└───────────┬─────────────┘
            │ 失败 → InvalidInputError
            ▼
┌─────────────────────────┐
│ 2. 提取 IV/密文/Tag     │
│    - IV: 前12字节       │
│    - Tag: 后16字节      │
│    - 密文: 中间部分     │
└───────────┬─────────────┘
            │ 格式错误 → InvalidInputError
            ▼
┌─────────────────────────┐
│ 3. 标准化密钥 (同加密)  │
└───────────┬─────────────┘
            │ 失败 → InvalidKeyError
            ▼
┌─────────────────────────┐
│ 4. AES-GCM解密          │
│    - 自动验证Tag        │
└───────────┬─────────────┘
            │ 失败 → DecryptionError
            ▼
┌─────────────────────────┐
│ 5. 校验输出为6位数字    │
└───────────┬─────────────┘
            │ 非预期 → DecryptionError
            ▼
输出: "123456"
```

---

## 6. 兼容性与迁移策略

| 类别 | 策略 |
|------|------|
| **Python版本** | 最低支持 Python 3.7+（使用 `typing.Union` 兼容旧语法） |
| **依赖管理** | 创建 `requirements.txt`，添加 `cryptography>=3.4` |
| **密钥格式兼容** | 支持 `bytes` 和 `Base64 str` 两种格式，方便不同场景使用 |
| **向后兼容** | 新模块独立，不影响现有 `test.py` |

---

## 7. 任务拆分

| 序号 | 任务 | 文件 | 验收点 |
|------|------|------|--------|
| 1 | 创建目录结构和异常类 | `six_digit_crypto/__init__.py`, `exceptions.py` | 异常可正常导入 |
| 2 | 实现输入校验模块 | `validation.py` | 6位数字/密钥校验通过 |
| 3 | 实现核心加密/解密逻辑 | `core.py` | AC1-AC5 全部通过 |
| 4 | 编写单元测试 | `tests/test_six_digit_crypto.py` | 覆盖率 > 90% |
| 5 | 添加依赖文件 | `requirements.txt` | `pip install -r` 成功 |
| 6 | 编写使用文档 | `six_digit_crypto/README.md`（可选） | 示例代码可运行 |

---

## 8. 风险、回滚与观测

### 8.1 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| 密钥泄露 | 文档明确建议使用环境变量或密钥管理服务 |
| IV复用攻击 | 每次加密生成随机IV（12字节，碰撞概率极低） |
| 密钥错误导致解密失败 | 明确异常类型，调用方可区分处理 |

### 8.2 日志策略

```python
# 建议（可选）：在核心函数中添加调试日志
import logging

logger = logging.getLogger(__name__)

def encrypt(...):
    logger.debug(f"Encrypting 6-digit input (length={len(six_digit)})")
    # ... 不记录明文和密钥
```

### 8.3 回滚方案

- 新模块独立，不修改现有代码
- 删除 `six_digit_crypto/` 目录即可完全回滚

---

## 9. 待确认点

| # | 问题 | 默认决策 | 理由 |
|---|------|----------|------|
| 1 | 输出格式是否需要固定长度？ | **否**，Base64可变长度 | AES-GCM输出长度固定，Base64编码后长度一致（约44字符） |
| 2 | 是否需要批量处理接口？ | **否** | 需求范围明确为单个处理 |
| 3 | 密钥是否需要提供生成工具？ | **是**，提供 `generate_key()` | 便于开发者快速使用 |
| 4 | 是否需要时间戳防重放？ | **否** | 由调用方在业务层实现 |

---

**请确认设计方案，或指出需要调整的部分。确认后我将开始实现代码。**
