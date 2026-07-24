from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash

from g2g import webhook_signature

FIXTURES = Path(__file__).parent / "fixtures"
ADMIN_PASSWORD = "correct horse battery staple"
ADMIN_PASSWORD_HASH = generate_password_hash(
    ADMIN_PASSWORD, method="pbkdf2:sha256:1000"
)
ADMIN_TOTP_SECRET = "JBSWY3DPEHPK3PXP"


def app_config(database_url: str, *, g2g_enabled: bool = False) -> dict[str, Any]:
    return {
        "TESTING": True,
        "APP_ENV": "testing",
        "PRODUCTION": False,
        "SECRET_KEY": "test-secret",
        "ACCESS_KEY_PEPPER": "test-pepper",
        "DATA_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "SQLALCHEMY_DATABASE_URI": database_url,
        "TOTP_SECRET": "JBSWY3DPEHPK3PXP",
        "TOTP_LABEL": "Test Account",
        "TOTP_ISSUER": "Test Software",
        "SOFTWARE_PROVIDER": "Gmail",
        "SOFTWARE_LOGIN_EMAIL": "test@example.com",
        "SOFTWARE_LOGIN_PASSWORD": "test-password",
        "PUBLIC_BASE_URL": "http://localhost",
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD_HASH": ADMIN_PASSWORD_HASH,
        "ADMIN_TOTP_SECRET": ADMIN_TOTP_SECRET,
        "G2G_INTEGRATION_ENABLED": g2g_enabled,
        "G2G_API_BASE": "https://open-api.g2g.com",
        "G2G_API_VERSION": "v2",
        "G2G_API_KEY": "test-api-key",
        "G2G_API_SECRET": "test-api-secret",
        "G2G_USER_ID": "685064",
        "G2G_WEBHOOK_SECRET": "test-webhook-secret",
        "G2G_WEBHOOK_CANONICAL_URL": "https://portal.example/webhooks/g2g",
        "G2G_WEBHOOK_MAX_AGE_SECONDS": 300,
        "G2G_REQUIRE_SELLER_MATCH": True,
        "G2G_PRODUCTS": {
            "G16704985465TEST": {
                "name": "Software access - 30 days",
                "duration_seconds": 30 * 86400,
                "max_quantity": 1,
            },
            "SECOND-OFFER": {
                "name": "Software access - 90 days",
                "duration_seconds": 90 * 86400,
                "max_quantity": 1,
            },
        },
        "G2G_DELIVERY_PATH_TEMPLATE": "/{version}/orders/{order_id}/delivery",
        "G2G_DELIVERY_STATUS_PATH_TEMPLATE": (
            "/{version}/orders/{order_id}/delivery/{delivery_id}"
        ),
        "G2G_DELIVERY_MAX_ATTEMPTS": 8,
        "G2G_DELIVERY_RETRY_BASE_SECONDS": 1,
        "G2G_DELIVERY_STALE_SECONDS": 1,
        "RATE_LIMIT_ATTEMPTS": 12,
        "RATE_LIMIT_WINDOW_SECONDS": 300,
        "MAX_ACTIVE_SESSIONS_PER_ORDER": 0,
        "MAX_DISTINCT_IPS_PER_ORDER": 0,
        "SKIP_MIGRATION_CHECK": True,
    }


def fixture(name: str, *, order_id: str | None = None, event_id: str | None = None):
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    payload["event_happened_at"] = int(time.time() * 1000)
    if order_id:
        payload["payload"]["order_id"] = order_id
    if event_id:
        payload["id"] = event_id
    return payload


def signed_headers(app, *, timestamp_ms: int | None = None) -> dict[str, str]:
    timestamp_ms = timestamp_ms or int(time.time() * 1000)
    with app.app_context():
        signature = webhook_signature(timestamp_ms=timestamp_ms)
    return {
        "g2g-signature": signature,
        "g2g-timestamp": str(timestamp_ms),
        "Content-Type": "application/json",
    }
