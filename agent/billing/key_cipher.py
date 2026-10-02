"""Authenticated encryption for API keys retained by the developer portal.

Authentication continues to use hashes. Encryption material lives outside SQLite.
"""
import base64
import os

from cryptography.fernet import Fernet, MultiFernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class KeyCipher:
    def __init__(self, keys):
        self.cipher = MultiFernet([Fernet(key) for key in keys])

    @classmethod
    def from_config(cls, app_secret=None):
        configured = os.environ.get("BILLING_KEY_ENCRYPTION_KEYS", "").strip()
        if configured:
            return cls([key.strip() for key in configured.split(",") if key.strip()])
        secret = app_secret or os.environ.get("APP_SECRET_KEY", "").strip()
        if not secret:
            return None
        # APP_SECRET_KEY is a high-entropy application secret, not a user password.
        derived = HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                       info=b"mirror-ai/billing-api-key/v1").derive(secret.encode())
        return cls([base64.urlsafe_b64encode(derived)])

    def encrypt(self, plaintext):
        return self.cipher.encrypt(plaintext.encode()).decode("ascii")

    def decrypt(self, ciphertext):
        return self.cipher.decrypt(ciphertext.encode("ascii")).decode()

    def rotate(self, ciphertext):
        return self.cipher.rotate(ciphertext.encode("ascii")).decode("ascii")
