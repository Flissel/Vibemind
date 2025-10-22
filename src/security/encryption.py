"""
Encryption utilities for secrets management using AES-256-GCM
"""
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Tuple


def encrypt_value(plaintext: str, master_key: bytes) -> Tuple[bytes, bytes]:
    """
    Encrypt a plaintext value using AES-256-GCM.

    Args:
        plaintext: The secret value to encrypt
        master_key: 32-byte master encryption key

    Returns:
        Tuple of (ciphertext, iv)
    """
    # Generate random IV (12 bytes for GCM)
    iv = os.urandom(12)

    # Create AESGCM cipher
    aesgcm = AESGCM(master_key)

    # Encrypt the plaintext
    ciphertext = aesgcm.encrypt(iv, plaintext.encode('utf-8'), None)

    return ciphertext, iv


def decrypt_value(ciphertext: bytes, iv: bytes, master_key: bytes) -> str:
    """
    Decrypt a ciphertext value using AES-256-GCM.

    Args:
        ciphertext: The encrypted value
        iv: Initialization vector used for encryption
        master_key: 32-byte master encryption key

    Returns:
        Decrypted plaintext string
    """
    # Create AESGCM cipher
    aesgcm = AESGCM(master_key)

    # Decrypt the ciphertext
    plaintext = aesgcm.decrypt(iv, ciphertext, None)

    return plaintext.decode('utf-8')


def derive_key_from_password(password: str, salt: bytes, iterations: int = 100000) -> bytes:
    """
    Derive a 32-byte encryption key from a password using PBKDF2.

    Args:
        password: Password to derive key from
        salt: Random salt for key derivation
        iterations: Number of PBKDF2 iterations (default: 100000)

    Returns:
        32-byte derived key
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(password.encode('utf-8'))
