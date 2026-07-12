from __future__ import annotations

import base64
import hashlib
import hmac
import os
import struct
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()


@dataclass(frozen=True)
class TOTPConfig:
    secret: str
    label: str
    issuer: str
    digits: int = 6
    period: int = 30
    algorithm: str = "SHA1"


def _clean_base32(value: str) -> str:
    return "".join(value.replace("-", " ").split()).upper()


def _decode_base32(secret: str) -> bytes:
    cleaned = _clean_base32(secret)
    if not cleaned:
        raise ValueError("TOTP secret is empty")
    padding = "=" * ((8 - len(cleaned) % 8) % 8)
    try:
        return base64.b32decode(cleaned + padding, casefold=True)
    except Exception as exc:
        raise ValueError("TOTP secret is not valid Base32") from exc


def _parse_totp_config(raw_value: str) -> TOTPConfig:
    raw_value = raw_value.strip()
    if not raw_value:
        raise ValueError("TOTP_SECRET is not configured in Render")

    fallback_label = os.getenv("TOTP_LABEL", "ChatGPT Test Account").strip() or "ChatGPT Test Account"
    fallback_issuer = os.getenv("TOTP_ISSUER", "OpenAI").strip() or "OpenAI"

    if not raw_value.lower().startswith("otpauth://"):
        _decode_base32(raw_value)
        return TOTPConfig(
            secret=_clean_base32(raw_value),
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
    _decode_base32(secret)

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
        secret=_clean_base32(secret),
        label=display_label,
        issuer=issuer,
        digits=digits,
        period=period,
        algorithm=algorithm,
    )


def generate_totp(config: TOTPConfig, timestamp: int | None = None) -> tuple[str, int]:
    now = int(time.time()) if timestamp is None else int(timestamp)
    counter = now // config.period
    key = _decode_base32(config.secret)
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


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

try:
    TOTP_CONFIG = _parse_totp_config(os.getenv("TOTP_SECRET", ""))
    TOTP_CONFIG_ERROR = ""
except (TypeError, ValueError) as exc:
    TOTP_CONFIG = None
    TOTP_CONFIG_ERROR = str(exc)


@app.after_request
def add_security_headers(response):
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "font-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'none'; "
        "form-action 'none'; "
        "object-src 'none'"
    )
    if request.is_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/health")
def health():
    return jsonify(status="ok", configured=TOTP_CONFIG is not None)


@app.get("/")
def index():
    if TOTP_CONFIG is None:
        return render_template("setup_error.html", error=TOTP_CONFIG_ERROR), 503
    return render_template(
        "index.html",
        label=TOTP_CONFIG.label,
        issuer=TOTP_CONFIG.issuer,
        period=TOTP_CONFIG.period,
    )


@app.get("/api/code")
def code_api():
    if TOTP_CONFIG is None:
        return jsonify(error=TOTP_CONFIG_ERROR or "TOTP is not configured"), 503
    code, remaining = generate_totp(TOTP_CONFIG)
    return jsonify(
        code=code,
        remaining=remaining,
        period=TOTP_CONFIG.period,
        label=TOTP_CONFIG.label,
        issuer=TOTP_CONFIG.issuer,
        server_time=int(time.time()),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
