from __future__ import annotations

import json
import os
from datetime import timedelta
from typing import Any

from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def normalize_database_url(value: str) -> str:
    value = value.strip()
    if value.startswith("postgres://"):
        return "postgresql+psycopg://" + value[len("postgres://") :]
    if value.startswith("postgresql://") and "+psycopg" not in value:
        return "postgresql+psycopg://" + value[len("postgresql://") :]
    return value


def parse_products(raw: str) -> dict[str, dict[str, Any]]:
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("G2G_PRODUCTS_JSON is not valid JSON") from exc

    if not isinstance(parsed, dict):
        raise ValueError("G2G_PRODUCTS_JSON must be a JSON object keyed by offer ID")

    products: dict[str, dict[str, Any]] = {}
    for offer_id, item in parsed.items():
        if not isinstance(item, dict):
            raise ValueError(f"Product {offer_id!r} must be a JSON object")

        name = str(item.get("name", "")).strip() or f"Offer {offer_id}"
        duration_seconds = item.get("duration_seconds")
        if duration_seconds is None:
            duration_hours = item.get("duration_hours")
            duration_days = item.get("duration_days")
            if duration_hours is not None:
                duration_seconds = int(duration_hours) * 3600
            elif duration_days is not None:
                duration_seconds = int(duration_days) * 86400

        try:
            duration_seconds = int(duration_seconds)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Product {offer_id!r} needs duration_seconds, duration_hours, or duration_days"
            ) from exc

        if duration_seconds < 60:
            raise ValueError(f"Product {offer_id!r} duration must be at least 60 seconds")

        products[str(offer_id)] = {
            "name": name,
            "duration_seconds": duration_seconds,
            "max_quantity": int(item.get("max_quantity", 1)),
        }
    return products


def build_config() -> dict[str, Any]:
    database_url = normalize_database_url(
        os.getenv("DATABASE_URL", "sqlite:///local.db")
    )
    return {
        "SECRET_KEY": os.getenv("SECRET_KEY", ""),
        "SQLALCHEMY_DATABASE_URI": database_url,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True},
        "MAX_CONTENT_LENGTH": 64 * 1024,
        "PERMANENT_SESSION_LIFETIME": timedelta(hours=12),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": env_bool("SESSION_COOKIE_SECURE", True),
        "ACCESS_KEY_PEPPER": os.getenv("ACCESS_KEY_PEPPER", ""),
        "DATA_ENCRYPTION_KEY": os.getenv("DATA_ENCRYPTION_KEY", ""),
        "TOTP_SECRET": os.getenv("TOTP_SECRET", ""),
        "TOTP_LABEL": os.getenv("TOTP_LABEL", "Software Account"),
        "TOTP_ISSUER": os.getenv("TOTP_ISSUER", "Software"),
        "SOFTWARE_PROVIDER": os.getenv("SOFTWARE_PROVIDER", "Email"),
        "SOFTWARE_LOGIN_EMAIL": os.getenv("SOFTWARE_LOGIN_EMAIL", ""),
        "SOFTWARE_LOGIN_PASSWORD": os.getenv("SOFTWARE_LOGIN_PASSWORD", ""),
        "PUBLIC_BASE_URL": os.getenv(
            "PUBLIC_BASE_URL", "http://127.0.0.1:5000"
        ).rstrip("/"),
        "G2G_INTEGRATION_ENABLED": env_bool("G2G_INTEGRATION_ENABLED", False),
        "G2G_API_BASE": os.getenv(
            "G2G_API_BASE", "https://open-api.g2g.com"
        ).rstrip("/"),
        "G2G_API_VERSION": os.getenv("G2G_API_VERSION", "v2").strip("/"),
        "G2G_API_KEY": os.getenv("G2G_API_KEY", ""),
        "G2G_API_SECRET": os.getenv("G2G_API_SECRET", ""),
        "G2G_USER_ID": os.getenv("G2G_USER_ID", ""),
        "G2G_WEBHOOK_SECRET": os.getenv("G2G_WEBHOOK_SECRET", ""),
        "G2G_WEBHOOK_CANONICAL_URL": os.getenv(
            "G2G_WEBHOOK_CANONICAL_URL",
            "http://127.0.0.1:5000/webhooks/g2g",
        ),
        "G2G_WEBHOOK_MAX_AGE_SECONDS": int(
            os.getenv("G2G_WEBHOOK_MAX_AGE_SECONDS", "300")
        ),
        "G2G_REQUIRE_SELLER_MATCH": env_bool(
            "G2G_REQUIRE_SELLER_MATCH", True
        ),
        "G2G_PRODUCTS": parse_products(os.getenv("G2G_PRODUCTS_JSON", "")),
        "G2G_DELIVERY_PATH_TEMPLATE": os.getenv(
            "G2G_DELIVERY_PATH_TEMPLATE",
            "/{version}/orders/{order_id}/delivery",
        ),
        "RATE_LIMIT_ATTEMPTS": int(os.getenv("RATE_LIMIT_ATTEMPTS", "12")),
        "RATE_LIMIT_WINDOW_SECONDS": int(
            os.getenv("RATE_LIMIT_WINDOW_SECONDS", "300")
        ),
    }


def configuration_errors(config: dict[str, Any]) -> list[str]:
    required = {
        "SECRET_KEY": config.get("SECRET_KEY"),
        "ACCESS_KEY_PEPPER": config.get("ACCESS_KEY_PEPPER"),
        "DATA_ENCRYPTION_KEY": config.get("DATA_ENCRYPTION_KEY"),
        "TOTP_SECRET": config.get("TOTP_SECRET"),
        "SOFTWARE_LOGIN_EMAIL": config.get("SOFTWARE_LOGIN_EMAIL"),
        "SOFTWARE_LOGIN_PASSWORD": config.get("SOFTWARE_LOGIN_PASSWORD"),
        "PUBLIC_BASE_URL": config.get("PUBLIC_BASE_URL"),
    }
    errors = [f"{name} is missing" for name, value in required.items() if not value]

    encryption_key = config.get("DATA_ENCRYPTION_KEY", "")
    if encryption_key:
        try:
            Fernet(encryption_key.encode("utf-8"))
        except Exception:
            errors.append("DATA_ENCRYPTION_KEY is not a valid Fernet key")

    if config.get("G2G_INTEGRATION_ENABLED"):
        g2g_required = {
            "G2G_API_KEY": config.get("G2G_API_KEY"),
            "G2G_API_SECRET": config.get("G2G_API_SECRET"),
            "G2G_USER_ID": config.get("G2G_USER_ID"),
            "G2G_WEBHOOK_SECRET": config.get("G2G_WEBHOOK_SECRET"),
            "G2G_WEBHOOK_CANONICAL_URL": config.get(
                "G2G_WEBHOOK_CANONICAL_URL"
            ),
        }
        errors.extend(
            f"{name} is missing while G2G integration is enabled"
            for name, value in g2g_required.items()
            if not value
        )
        if not config.get("G2G_PRODUCTS"):
            errors.append(
                "G2G_PRODUCTS_JSON has no products while G2G integration is enabled"
            )

    return errors
