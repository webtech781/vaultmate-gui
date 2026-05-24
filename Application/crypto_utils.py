import base64
import os
import keyring
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet

SERVICE_NAME = "VaultMateGUI"

def derive_key(password: str, salt: bytes) -> bytes:
    """Derives a secure cryptographic key from a password and a salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt_data(data: str, key: bytes) -> str:
    """Encrypts plaintext data using a derived key."""
    if not data:
        return ""
    f = Fernet(key)
    return f.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str, key: bytes) -> str:
    """Decrypts ciphertext using a derived key."""
    if not encrypted_data:
        return ""
    f = Fernet(key)
    try:
        return f.decrypt(encrypted_data.encode()).decode()
    except Exception:
        # If decryption fails (e.g. wrong key)
        return ""

def save_to_keyring(username: str, password: str):
    """Saves the master password to the OS keyring."""
    keyring.set_password(SERVICE_NAME, username, password)

def get_from_keyring(username: str) -> str:
    """Retrieves the master password from the OS keyring."""
    return keyring.get_password(SERVICE_NAME, username)

def delete_from_keyring(username: str):
    """Deletes the master password from the OS keyring."""
    try:
        keyring.delete_password(SERVICE_NAME, username)
    except keyring.errors.PasswordDeleteError:
        pass
