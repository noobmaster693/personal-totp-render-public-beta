from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Mapping
from typing import Any

import requests
from flask import current_app


class G2GError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_data: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class G2GConflictError(G2GError):
    pass


def _hmac_hex(secret: str, message: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def signed_api_headers(path: str, *, timestamp_ms: int | None = None) -> dict[str, str]:
    timestamp = str(
        int(time.time() * 1000) if timestamp_ms is None else int(timestamp_ms)
    )
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


def verify_webhook_signature(
    headers: Mapping[str, str], *, now_ms: int | None = None
) -> tuple[bool, str]:
    """Verify the documented webhook headers.

    G2G's webhook examples send only ``g2g-signature`` and ``g2g-timestamp``.
    The API key and user ID are still part of the signature input, but they are
    taken from our configured seller credentials. If G2G also sends those
    identity headers, they are checked as an additional defence.
    """

    signature = headers.get("g2g-signature", "")
    timestamp = headers.get("g2g-timestamp", "")
    if not signature or not timestamp:
        return False, "missing signature headers"

    api_key = current_app.config["G2G_API_KEY"]
    user_id = current_app.config["G2G_USER_ID"]
    supplied_api_key = headers.get("g2g-api-key")
    supplied_user_id = headers.get("g2g-userid")
    if supplied_api_key and not hmac.compare_digest(supplied_api_key, api_key):
        return False, "unexpected API key"
    if supplied_user_id and not hmac.compare_digest(supplied_user_id, user_id):
        return False, "unexpected G2G user ID"

    try:
        timestamp_ms = int(timestamp)
    except ValueError:
        return False, "invalid timestamp"

    current_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    age_seconds = abs((current_ms - timestamp_ms) / 1000)
    if age_seconds > int(current_app.config["G2G_WEBHOOK_MAX_AGE_SECONDS"]):
        return False, "stale webhook"

    canonical = (
        current_app.config["G2G_WEBHOOK_CANONICAL_URL"] + api_key + user_id + timestamp
    )
    expected = _hmac_hex(current_app.config["G2G_WEBHOOK_SECRET"], canonical)
    if not hmac.compare_digest(expected.lower(), signature.lower()):
        return False, "signature mismatch"
    return True, "ok"


def webhook_signature(*, timestamp_ms: int) -> str:
    """Build a webhook signature for local fixtures and integration tests."""

    canonical = (
        current_app.config["G2G_WEBHOOK_CANONICAL_URL"]
        + current_app.config["G2G_API_KEY"]
        + current_app.config["G2G_USER_ID"]
        + str(int(timestamp_ms))
    )
    return _hmac_hex(current_app.config["G2G_WEBHOOK_SECRET"], canonical)


def _path(template_name: str, **values: str) -> str:
    template = current_app.config[template_name]
    path = template.format(version=current_app.config["G2G_API_VERSION"], **values)
    return path if path.startswith("/") else "/" + path


def _response_data(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {"raw": response.text[:1000]}


def _request(
    method: str,
    path: str,
    *,
    json_payload: dict[str, Any] | None = None,
) -> tuple[Any, int]:
    url = current_app.config["G2G_API_BASE"] + path
    try:
        response = requests.request(
            method,
            url,
            headers=signed_api_headers(path),
            json=json_payload,
            timeout=20,
        )
    except requests.RequestException as exc:
        raise G2GError(f"Could not contact G2G: {exc}") from exc

    data = _response_data(response)
    if response.status_code == 409:
        raise G2GConflictError(
            "G2G reported a delivery conflict",
            status_code=409,
            response_data=data,
        )
    if not response.ok:
        detail = data.get("raw", "") if isinstance(data, dict) else str(data)
        raise G2GError(
            f"G2G request failed with HTTP {response.status_code}: {detail[:500]}",
            status_code=response.status_code,
            response_data=data,
        )
    return data, response.status_code


def get_deliveries(order_id: str) -> dict[str, Any]:
    path = _path("G2G_DELIVERY_PATH_TEMPLATE", order_id=order_id)
    data, status_code = _request("GET", path)
    return {"data": data, "status_code": status_code}


def get_delivery_status(order_id: str, delivery_id: str) -> dict[str, Any]:
    path = _path(
        "G2G_DELIVERY_STATUS_PATH_TEMPLATE",
        order_id=order_id,
        delivery_id=delivery_id,
    )
    data, status_code = _request("GET", path)
    return {"data": data, "status_code": status_code}


def deliver_code(
    *,
    order_id: str,
    delivery_id: str,
    content: str,
    reference_id: str,
) -> dict[str, Any]:
    path = _path("G2G_DELIVERY_PATH_TEMPLATE", order_id=order_id)
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
    data, status_code = _request("POST", path, json_payload=payload)
    return {"data": data, "status_code": status_code}


def _walk_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def delivery_candidates(value: Any) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in _walk_dicts(value):
        delivery_id = str(item.get("delivery_id") or "").strip()
        if not delivery_id or delivery_id in seen:
            continue
        seen.add(delivery_id)
        candidates.append(item)
    return candidates


def resolve_delivery_id(
    *,
    order_id: str,
    webhook_payload: dict[str, Any],
    offer_id: str,
) -> str:
    candidates = delivery_candidates(webhook_payload)
    if not candidates:
        candidates = delivery_candidates(get_deliveries(order_id)["data"])

    if not candidates:
        raise G2GError(
            "G2G did not provide a delivery_id in the webhook or Get Deliveries response"
        )

    offer_matches = [
        item
        for item in candidates
        if str(item.get("offer_id") or "").strip() == str(offer_id)
    ]
    pool = offer_matches or candidates
    pending = [
        item
        for item in pool
        if str(item.get("delivery_status") or item.get("status") or "").lower()
        not in {"delivered", "completed", "success", "succeeded"}
    ]
    pool = pending or pool
    identifiers = {str(item.get("delivery_id") or "").strip() for item in pool}
    identifiers.discard("")
    if len(identifiers) != 1:
        raise G2GError(
            "G2G returned multiple possible delivery IDs; refusing an ambiguous delivery"
        )
    return next(iter(identifiers))


def delivery_status_value(value: Any) -> str | None:
    records = list(_walk_dicts(value))
    for item in records:
        for key in ("delivery_status", "delivery_state"):
            status = item.get(key)
            if isinstance(status, str) and status.strip():
                return status.strip().lower()
    for item in records:
        if not item.get("delivery_id"):
            continue
        status = item.get("status")
        if isinstance(status, str) and status.strip():
            return status.strip().lower()
    return None


def delivery_is_complete(value: Any) -> bool:
    return delivery_status_value(value) in {
        "delivered",
        "completed",
        "complete",
        "success",
        "succeeded",
    }
