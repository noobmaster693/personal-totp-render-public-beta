from __future__ import annotations

import json
import os
from datetime import timedelta
from typing import Any
from urllib.parse import urlparse

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
        raise TypeError("G2G_PRODUCTS_JSON must be a JSON object keyed by offer ID")

    products: dict[str, dict[str, Any]] = {}
    for offer_id, item in parsed.items():
        if not isinstance(item, dict):
            raise TypeError(f"Product {offer_id!r} must be a JSON object")

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
            raise ValueError(
                f"Product {offer_id!r} duration must be at least 60 seconds"
            )

        max_quantity = int(item.get("max_quantity", 1))
        if max_quantity < 1:
            raise ValueError(f"Product {offer_id!r} max_quantity must be positive")

        products[str(offer_id)] = {
            "name": name,
            "duration_seconds": duration_seconds,
            "max_quantity": max_quantity,
        }
    return products


def build_config() -> dict[str, Any]:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    production = app_env == "production"
    database_url = normalize_database_url(
        os.getenv("DATABASE_URL", "" if production else "sqlite:///local.db")
    )
    public_base_url = os.getenv(
        "PUBLIC_BASE_URL", "" if production else "http://127.0.0.1:5000"
    ).rstrip("/")
    webhook_url = os.getenv(
        "G2G_WEBHOOK_CANONICAL_URL",
        "" if production else "http://127.0.0.1:5000/webhooks/g2g",
    ).rstrip("/")

    return {
        "APP_ENV": app_env,
        "PRODUCTION": production,
        "SECRET_KEY": os.getenv("SECRET_KEY", ""),
        "SQLALCHEMY_DATABASE_URI": database_url,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True},
        "MAX_CONTENT_LENGTH": 64 * 1024,
        "PERMANENT_SESSION_LIFETIME": timedelta(hours=12),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": env_bool("SESSION_COOKIE_SECURE", bool(production)),
        "ACCESS_KEY_PEPPER": os.getenv("ACCESS_KEY_PEPPER", ""),
        "DATA_ENCRYPTION_KEY": os.getenv("DATA_ENCRYPTION_KEY", ""),
        "TOTP_SECRET": os.getenv("TOTP_SECRET", ""),
        "TOTP_LABEL": os.getenv("TOTP_LABEL", "Software Account"),
        "TOTP_ISSUER": os.getenv("TOTP_ISSUER", "Software"),
        "SOFTWARE_PROVIDER": os.getenv("SOFTWARE_PROVIDER", "Email"),
        "SOFTWARE_LOGIN_EMAIL": os.getenv("SOFTWARE_LOGIN_EMAIL", ""),
        "SOFTWARE_LOGIN_PASSWORD": os.getenv("SOFTWARE_LOGIN_PASSWORD", ""),
        "PUBLIC_BASE_URL": public_base_url,
        "ADMIN_USERNAME": os.getenv("ADMIN_USERNAME", ""),
        "ADMIN_PASSWORD_HASH": os.getenv("ADMIN_PASSWORD_HASH", ""),
        "ADMIN_TOTP_SECRET": os.getenv("ADMIN_TOTP_SECRET", ""),
        "ADMIN_SESSION_HOURS": int(os.getenv("ADMIN_SESSION_HOURS", "4")),
        "ADMIN_LOGIN_ATTEMPTS": int(os.getenv("ADMIN_LOGIN_ATTEMPTS", "10")),
        "ADMIN_LOGIN_WINDOW_SECONDS": int(
            os.getenv("ADMIN_LOGIN_WINDOW_SECONDS", "900")
        ),
        "G2G_INTEGRATION_ENABLED": env_bool("G2G_INTEGRATION_ENABLED", False),
        "G2G_API_BASE": os.getenv("G2G_API_BASE", "https://open-api.g2g.com").rstrip(
            "/"
        ),
        "G2G_API_VERSION": os.getenv("G2G_API_VERSION", "v2").strip("/"),
        "G2G_API_KEY": os.getenv("G2G_API_KEY", ""),
        "G2G_API_SECRET": os.getenv("G2G_API_SECRET", ""),
        "G2G_USER_ID": os.getenv("G2G_USER_ID", ""),
        "G2G_WEBHOOK_SECRET": os.getenv("G2G_WEBHOOK_SECRET", ""),
        "G2G_WEBHOOK_CANONICAL_URL": webhook_url,
        "G2G_WEBHOOK_MAX_AGE_SECONDS": int(
            os.getenv("G2G_WEBHOOK_MAX_AGE_SECONDS", "300")
        ),
        "G2G_REQUIRE_SELLER_MATCH": env_bool("G2G_REQUIRE_SELLER_MATCH", True),
        "G2G_PRODUCTS": parse_products(os.getenv("G2G_PRODUCTS_JSON", "")),
        "G2G_DELIVERY_PATH_TEMPLATE": os.getenv(
            "G2G_DELIVERY_PATH_TEMPLATE",
            "/{version}/orders/{order_id}/delivery",
        ),
        "G2G_DELIVERY_STATUS_PATH_TEMPLATE": os.getenv(
            "G2G_DELIVERY_STATUS_PATH_TEMPLATE",
            "/{version}/orders/{order_id}/delivery/{delivery_id}",
        ),
        "G2G_DELIVERY_MAX_ATTEMPTS": int(os.getenv("G2G_DELIVERY_MAX_ATTEMPTS", "8")),
        "G2G_DELIVERY_RETRY_BASE_SECONDS": int(
            os.getenv("G2G_DELIVERY_RETRY_BASE_SECONDS", "60")
        ),
        "G2G_DELIVERY_STALE_SECONDS": int(
            os.getenv("G2G_DELIVERY_STALE_SECONDS", "120")
        ),
        "RATE_LIMIT_ATTEMPTS": int(os.getenv("RATE_LIMIT_ATTEMPTS", "12")),
        "RATE_LIMIT_WINDOW_SECONDS": int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "300")),
        "MAX_ACTIVE_SESSIONS_PER_ORDER": int(
            os.getenv("MAX_ACTIVE_SESSIONS_PER_ORDER", "0")
        ),
        "MAX_DISTINCT_IPS_PER_ORDER": int(os.getenv("MAX_DISTINCT_IPS_PER_ORDER", "0")),
        "MIGRATION_HEAD": "20260724_0001",
        "SKIP_MIGRATION_CHECK": False,
    }


def _https_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme == "https" and bool(parsed.netloc)


def configuration_errors(config: dict[str, Any]) -> list[str]:
    required = {
        "SECRET_KEY": config.get("SECRET_KEY"),
        "ACCESS_KEY_PEPPER": config.get("ACCESS_KEY_PEPPER"),
        "DATA_ENCRYPTION_KEY": config.get("DATA_ENCRYPTION_KEY"),
        "DATABASE_URL": config.get("SQLALCHEMY_DATABASE_URI"),
        "PUBLIC_BASE_URL": config.get("PUBLIC_BASE_URL"),
        "ADMIN_USERNAME": config.get("ADMIN_USERNAME"),
        "ADMIN_PASSWORD_HASH": config.get("ADMIN_PASSWORD_HASH"),
    }
    errors = [f"{name} is missing" for name, value in required.items() if not value]

    encryption_key = config.get("DATA_ENCRYPTION_KEY", "")
    if encryption_key:
        try:
            Fernet(encryption_key.encode("utf-8"))
        except (TypeError, ValueError):
            errors.append("DATA_ENCRYPTION_KEY is not a valid Fernet key")

    if config.get("PRODUCTION"):
        database_url = str(config.get("SQLALCHEMY_DATABASE_URI", ""))
        if not database_url.startswith("postgresql+psycopg://"):
            errors.append("Production requires a PostgreSQL DATABASE_URL")
        if not _https_url(str(config.get("PUBLIC_BASE_URL", ""))):
            errors.append("Production PUBLIC_BASE_URL must be HTTPS")
        if not config.get("SESSION_COOKIE_SECURE"):
            errors.append("Production requires SESSION_COOKIE_SECURE=true")
        if not config.get("ADMIN_TOTP_SECRET"):
            errors.append("Production requires a separate ADMIN_TOTP_SECRET")

    if config.get("G2G_INTEGRATION_ENABLED"):
        g2g_required = {
            "G2G_API_KEY": config.get("G2G_API_KEY"),
            "G2G_API_SECRET": config.get("G2G_API_SECRET"),
            "G2G_USER_ID": config.get("G2G_USER_ID"),
            "G2G_WEBHOOK_SECRET": config.get("G2G_WEBHOOK_SECRET"),
            "G2G_WEBHOOK_CANONICAL_URL": config.get("G2G_WEBHOOK_CANONICAL_URL"),
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
        if config.get("PRODUCTION") and not _https_url(
            str(config.get("G2G_WEBHOOK_CANONICAL_URL", ""))
        ):
            errors.append("Production G2G_WEBHOOK_CANONICAL_URL must be HTTPS")

    return errors
