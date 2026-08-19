"""AES-256-GCM 加密模块

说明：
- 使用 argon2.low_level.hash_secret_raw 进行**确定性**密钥派生，
  相同 (密码, salt) 必得相同密钥，这是解锁、改密校验的基础。
- 密文格式：base64( nonce(12B) + ciphertext+tag )，salt 存于 vault_meta。
"""
import base64
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2.low_level import hash_secret_raw, Type


SALT_LEN = 16
NONCE_LEN = 12
KEY_LEN = 32


class VaultCrypto:
    def __init__(self, password: str, salt: bytes = None):
        self.salt = salt or secrets.token_bytes(SALT_LEN)
        self._derive_key(password)
        self.cipher = AESGCM(self.key)

    def _derive_key(self, password: str):
        # Argon2id 原始哈希：确定性派生 32 字节密钥
        self.key = hash_secret_raw(
            secret=password.encode("utf-8"),
            salt=self.salt,
            time_cost=3,
            memory_cost=65536,   # 64 MB
            parallelism=4,
            hash_len=KEY_LEN,
            type=Type.ID,
        )

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        nonce = secrets.token_bytes(NONCE_LEN)
        ciphertext = self.cipher.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(nonce + ciphertext).decode()

    def decrypt(self, ciphertext_b64: str) -> str:
        if not ciphertext_b64:
            return ""
        try:
            data = base64.b64decode(ciphertext_b64)
            nonce, ciphertext = data[:NONCE_LEN], data[NONCE_LEN:]
            plaintext = self.cipher.decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8")
        except Exception:
            return "[解密失败]"

    def get_salt_b64(self) -> str:
        return base64.b64encode(self.salt).decode()

    @classmethod
    def from_salt_b64(cls, password: str, salt_b64: str):
        salt = base64.b64decode(salt_b64)
        return cls(password, salt)
