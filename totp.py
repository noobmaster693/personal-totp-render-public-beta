from __future__ import annotations

import base64
import hashlib
import hmac
import struct
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse


@dataclass(frozen=True)
class TOTPConfig:
    secret: str
    label: str
    issuer: str
    digits: int = 6
    period: int = 30
    algorithm: str = "SHA1"


def clean_base32(value: str) -> str:
    return "".join(value.replace("-", " ").split()).upper()


def decode_base32(secret: str) -> bytes:
    cleaned = clean_base32(secret)
    if not cleaned:
        raise ValueError("TOTP secret is empty")
    padding = "=" * ((8 - len(cleaned) % 8) % 8)
    try:
        return base64.b32decode(cleaned + padding, casefold=True)
    except Exception as exc:
        raise ValueError("TOTP secret is not valid Base32") from exc


def parse_totp_config(
    raw_value: str,
    fallback_label: str = "Software Account",
    fallback_issuer: str = "Software",
) -> TOTPConfig:
    raw_value = raw_value.strip()
    if not raw_value:
        raise ValueError("TOTP_SECRET is not configured")

    fallback_label = fallback_label.strip() or "Software Account"
    fallback_issuer = fallback_issuer.strip() or "Software"

    if not raw_value.lower().startswith("otpauth://"):
        decode_base32(raw_value)
        return TOTPConfig(
            secret=clean_base32(raw_value),
            label=fallback_label,
            issuer=fallback_issuer,
        )

    parsed = urlparse(raw_value)
    if parsed.scheme.lower() != "otpauth" or parsed.netloc.lower() != "totp":
        raise ValueError("TOTP_SECRET must be a Base32 key or an otpauth://totp URI")

    params = parse_qs(parsed.query)
    secret = params.get("secret", [""])[0]
    if not secret:
        raise ValueError("The otpauth URI has no secret parameter")
    decode_base32(secret)

    try:
        digits = int(params.get("digits", ["6"])[0])
        period = int(params.get("period", ["30"])[0])
    except ValueError as exc:
        raise ValueError("The otpauth URI contains invalid numeric settings") from exc

    algorithm = params.get("algorithm", ["SHA1"])[0].upper()
    if digits not in {6, 7, 8}:
        raise ValueError("TOTP digits must be 6, 7, or 8")
    if not 15 <= period <= 120:
        raise ValueError("TOTP period must be between 15 and 120 seconds")
    if algorithm not in {"SHA1", "SHA256", "SHA512"}:
        raise ValueError("Unsupported TOTP algorithm")

    uri_label = unquote(parsed.path.lstrip("/")) or fallback_label
    issuer = params.get("issuer", [fallback_issuer])[0].strip() or fallback_issuer
    display_label = uri_label.split(":", 1)[-1].strip() or fallback_label

    return TOTPConfig(
        secret=clean_base32(secret),
        label=display_label,
        issuer=issuer,
        digits=digits,
        period=period,
        algorithm=algorithm,
    )


def generate_totp(
    config: TOTPConfig, timestamp: int | None = None
) -> tuple[str, int]:
    now = int(time.time()) if timestamp is None else int(timestamp)
    counter = now // config.period
    key = decode_base32(config.secret)
    digest_function = {
        "SHA1": hashlib.sha1,
        "SHA256": hashlib.sha256,
        "SHA512": hashlib.sha512,
    }[config.algorithm]
    digest = hmac.new(key, struct.pack(">Q", counter), digest_function).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    code = str(binary % (10**config.digits)).zfill(config.digits)
    remaining = config.period - (now % config.period)
    return code, remaining
