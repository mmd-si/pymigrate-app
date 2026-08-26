import base64
import hashlib
import hmac
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

def sha256hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def sha256hmac(text: str, secret: str) -> str:
    return hmac.new(secret.encode('utf-8'), text.encode('utf-8'), hashlib.sha256).hexdigest()

def verify_hmac(text: str, signature: str, secret: str) -> bool:
    return hmac.compare_digest(sha256hmac(text, secret), signature)

def encrypt(text: str, key: bytes, iv: bytes) -> str:
    btext = text.encode()
    pad_len = 16 - (len(btext) % 16)
    padded = btext + bytes([pad_len] * pad_len)

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(encrypted).decode()

def decrypt(text: str, key: bytes, iv: bytes) -> str:
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    raw = decryptor.update(base64.b64decode(text)) + decryptor.finalize()

    pad_len = raw[-1]
    if not 1 <= pad_len <= 16 or raw[-pad_len:] != bytes([pad_len]) * pad_len:
        raise ValueError('Invalid padding')
    return raw[:-pad_len].decode()
