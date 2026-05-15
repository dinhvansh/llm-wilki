from __future__ import annotations

import base64
import copy
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


SECRET_PREFIX = "enc:v1:"


def _fernet_key() -> bytes:
    source = settings.RUNTIME_SECRET_ENCRYPTION_KEY or settings.SECRET_KEY
    candidate = str(source or "").strip()
    if candidate:
        try:
            raw = base64.urlsafe_b64decode(candidate.encode("utf-8"))
            if len(raw) == 32:
                return candidate.encode("utf-8")
        except Exception:
            pass
    digest = hashlib.sha256(candidate.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _fernet() -> Fernet:
    return Fernet(_fernet_key())


def is_encrypted_secret(value: object) -> bool:
    return isinstance(value, str) and value.startswith(SECRET_PREFIX)


def encrypt_secret(value: object) -> str:
    secret = str(value or "").strip()
    if not secret or is_encrypted_secret(secret):
        return secret
    token = _fernet().encrypt(secret.encode("utf-8")).decode("utf-8")
    return f"{SECRET_PREFIX}{token}"


def decrypt_secret(value: object) -> str:
    secret = str(value or "").strip()
    if not secret:
        return ""
    if not is_encrypted_secret(secret):
        return secret
    token = secret.removeprefix(SECRET_PREFIX)
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""


def encrypt_task_profiles(profiles: dict | None) -> dict:
    encrypted = copy.deepcopy(profiles or {})
    for profile in encrypted.values():
        if isinstance(profile, dict):
            profile["apiKey"] = encrypt_secret(profile.get("apiKey", ""))
    return encrypted


def decrypt_task_profiles(profiles: dict | None) -> dict:
    decrypted = copy.deepcopy(profiles or {})
    for profile in decrypted.values():
        if isinstance(profile, dict):
            profile["apiKey"] = decrypt_secret(profile.get("apiKey", ""))
    return decrypted
