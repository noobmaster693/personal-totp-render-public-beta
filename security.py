from __future__ import annotations

import hashlib
import hmac
import secrets

from cryptography.fernet import Fernet
from flask import current_app


def _fernet() -> Fernet:
    key = current_app.config["DATA_ENCRYPTION_KEY"]
    return Fernet(key.encode("utf-8"))


def encrypt_text(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_text(value: str) -> str:
    return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")


def generate_access_key() -> str:
    raw = secrets.token_hex(16).upper()
    groups = [raw[index : index + 4] for index in range(0, len(raw), 4)]
    return "ACCESS-" + "-".join(groups)


def _purpose_hash(purpose: str, value: str) -> str:
    pepper = current_app.config["ACCESS_KEY_PEPPER"].encode("utf-8")
    message = f"{purpose}\0{value}".encode()
    return hmac.new(pepper, message, hashlib.sha256).hexdigest()


def hash_access_key(value: str) -> str:
    pepper = current_app.config["ACCESS_KEY_PEPPER"].encode("utf-8")
    normalized = value.strip().upper().encode("utf-8")
    return hmac.new(pepper, normalized, hashlib.sha256).hexdigest()


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(value: str) -> str:
    return _purpose_hash("buyer-session", value.strip())


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)
