"""
Cryptographic utilities for HideX.

All cryptographic operations are designed for:
- Local-only storage
- Secure encryption of sensitive data
- No transmission of private keys
"""

import hashlib
import secrets
import base64
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def generate_id(prefix: str = "") -> str:
    """
    Generate a unique identifier.
    
    Uses cryptographically secure random bytes.
    """
    random_hex = secrets.token_hex(16)
    if prefix:
        return f"{prefix}_{random_hex}"
    return random_hex


def hash_data(data: str, algorithm: str = "sha256") -> str:
    """
    Hash data using specified algorithm.
    
    Used for audit log integrity and data verification.
    """
    if algorithm == "sha256":
        return hashlib.sha256(data.encode()).hexdigest()
    elif algorithm == "sha512":
        return hashlib.sha512(data.encode()).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


def derive_key(password: str, salt: bytes) -> bytes:
    """
    Derive encryption key from password using PBKDF2.
    
    Uses high iteration count for security.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,  # High iteration count for security
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def encrypt_data(data: str, password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
    """
    Encrypt data with password-derived key.
    
    Returns (encrypted_data, salt) tuple.
    Never transmit the password or salt over network.
    """
    if salt is None:
        salt = secrets.token_bytes(16)
    
    key = derive_key(password, salt)
    fernet = Fernet(key)
    encrypted = fernet.encrypt(data.encode())
    
    return encrypted, salt


def decrypt_data(encrypted_data: bytes, password: str, salt: bytes) -> str:
    """
    Decrypt data with password-derived key.
    
    Raises exception if password is incorrect.
    """
    key = derive_key(password, salt)
    fernet = Fernet(key)
    decrypted = fernet.decrypt(encrypted_data)
    
    return decrypted.decode()


def generate_secure_password(length: int = 32) -> str:
    """Generate a cryptographically secure random password."""
    return secrets.token_urlsafe(length)
