from six_digit_crypto import encrypt, decrypt, generate_key

# 生成密钥
key = generate_key()

# 加密
cipher = encrypt("123456", key)
print("加密后：", cipher)
# 解密
original = decrypt(cipher, key)
print("解密后：", original)