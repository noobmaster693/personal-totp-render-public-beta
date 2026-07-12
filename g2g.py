from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Mapping
from typing import Any

import requests
from flask import current_app


class G2GError(RuntimeError):
    pass


def _hmac_hex(secret: str, message: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def signed_api_headers(path: str) -> dict[str, str]:
    timestamp = str(int(time.time() * 1000))
    api_key = current_app.config["G2G_API_KEY"]
    user_id = current_app.config["G2G_USER_ID"]
    secret = current_app.config["G2G_API_SECRET"]
    canonical = path + api_key + user_id + timestamp
    return {
        "g2g-api-key": api_key,
        "g2g-userid": user_id,
        "g2g-signature": _hmac_hex(secret, canonical),
        "g2g-timestamp": timestamp,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def verify_webhook_signature(headers: Mapping[str, str]) -> tuple[bool, str]:
    api_key = headers.get("g2g-api-key", "")
    user_id = headers.get("g2g-userid", "")
    signature = headers.get("g2g-signature", "")
    timestamp = headers.get("g2g-timestamp", "")

    if not all([api_key, user_id, signature, timestamp]):
        return False, "missing signature headers"
    if api_key != current_app.config["G2G_API_KEY"]:
        return False, "unexpected API key"
    if user_id != current_app.config["G2G_USER_ID"]:
        return False, "unexpected G2G user ID"

    try:
        timestamp_ms = int(timestamp)
    except ValueError:
        return False, "invalid timestamp"

    age_seconds = abs((int(time.time() * 1000) - timestamp_ms) / 1000)
    if age_seconds > int(current_app.config["G2G_WEBHOOK_MAX_AGE_SECONDS"]):
        return False, "stale webhook"

    canonical = (
        current_app.config["G2G_WEBHOOK_CANONICAL_URL"]
        + api_key
        + user_id
        + timestamp
    )
    expected = _hmac_hex(
        current_app.config["G2G_WEBHOOK_SECRET"], canonical
    )
    if not hmac.compare_digest(expected.lower(), signature.lower()):
        return False, "signature mismatch"
    return True, "ok"


def deliver_code(
    *,
    order_id: str,
    delivery_id: str,
    content: str,
    reference_id: str,
) -> dict[str, Any]:
    template = current_app.config["G2G_DELIVERY_PATH_TEMPLATE"]
    path = template.format(
        version=current_app.config["G2G_API_VERSION"],
        order_id=order_id,
    )
    if not path.startswith("/"):
        path = "/" + path

    url = current_app.config["G2G_API_BASE"] + path
    payload = {
        "delivery_id": delivery_id,
        "codes": [
            {
                "content": content,
                "content_type": "text/plain",
                "reference_id": reference_id,
            }
        ],
    }

    try:
        response = requests.post(
            url,
            headers=signed_api_headers(path),
            json=payload,
            timeout=20,
        )
    except requests.RequestException as exc:
        raise G2GError(f"Could not contact G2G: {exc}") from exc

    if response.status_code == 409:
        return {"duplicate": True, "status_code": 409}

    if not response.ok:
        raise G2GError(
            f"G2G delivery failed with HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    try:
        return response.json()
    except ValueError:
        return {"status_code": response.status_code, "raw": response.text[:500]}
