from __future__ import annotations

from dataclasses import dataclass

from flask import current_app

from extensions import db
from models import PortalSettings
from security import decrypt_text, encrypt_text
from totp import TOTPConfig, parse_totp_config


@dataclass(frozen=True)
class AccountSettings:
    provider: str
    login_email: str
    login_password: str
    totp_raw: str
    totp: TOTPConfig


def _decrypt_or_default(ciphertext: str | None, default: str) -> str:
    if not ciphertext:
        return default
    return decrypt_text(ciphertext)


def get_settings_record() -> PortalSettings | None:
    return db.session.get(PortalSettings, 1)


def get_account_settings() -> AccountSettings:
    record = get_settings_record()
    provider = current_app.config.get("SOFTWARE_PROVIDER", "")
    email = current_app.config.get("SOFTWARE_LOGIN_EMAIL", "")
    password = current_app.config.get("SOFTWARE_LOGIN_PASSWORD", "")
    totp_raw = current_app.config.get("TOTP_SECRET", "")
    label = current_app.config.get("TOTP_LABEL", "Software Account")
    issuer = current_app.config.get("TOTP_ISSUER", "Software")

    if record is not None:
        provider = _decrypt_or_default(record.provider_ciphertext, provider)
        email = _decrypt_or_default(record.login_email_ciphertext, email)
        password = _decrypt_or_default(record.login_password_ciphertext, password)
        totp_raw = _decrypt_or_default(record.totp_secret_ciphertext, totp_raw)
        label = record.totp_label or label
        issuer = record.totp_issuer or issuer

    missing = [
        name
        for name, value in {
            "software provider": provider,
            "software login email": email,
            "software login password": password,
            "TOTP secret": totp_raw,
        }.items()
        if not str(value).strip()
    ]
    if missing:
        raise ValueError("Missing account settings: " + ", ".join(missing))

    totp = parse_totp_config(totp_raw, label, issuer)
    return AccountSettings(
        provider=str(provider).strip(),
        login_email=str(email).strip(),
        login_password=str(password),
        totp_raw=str(totp_raw),
        totp=totp,
    )


def save_account_settings(
    *,
    provider: str,
    login_email: str,
    login_password: str | None,
    totp_secret: str | None,
    totp_label: str,
    totp_issuer: str,
) -> PortalSettings:
    provider = provider.strip()
    login_email = login_email.strip()
    totp_label = totp_label.strip() or "Software Account"
    totp_issuer = totp_issuer.strip() or "Software"
    if not provider or not login_email:
        raise ValueError("Provider and login email are required")

    record = get_settings_record()
    if record is None:
        record = PortalSettings(id=1)
        db.session.add(record)

    if login_password is not None and login_password:
        record.login_password_ciphertext = encrypt_text(login_password)
    if totp_secret is not None and totp_secret.strip():
        parse_totp_config(totp_secret, totp_label, totp_issuer)
        record.totp_secret_ciphertext = encrypt_text(totp_secret.strip())

    existing_password = bool(
        record.login_password_ciphertext
        or current_app.config.get("SOFTWARE_LOGIN_PASSWORD")
    )
    existing_totp = bool(
        record.totp_secret_ciphertext or current_app.config.get("TOTP_SECRET")
    )
    if not existing_password:
        raise ValueError("A software login password is required")
    if not existing_totp:
        raise ValueError("A TOTP secret is required")

    record.provider_ciphertext = encrypt_text(provider)
    record.login_email_ciphertext = encrypt_text(login_email)
    record.totp_label = totp_label
    record.totp_issuer = totp_issuer
    db.session.commit()
    return record
