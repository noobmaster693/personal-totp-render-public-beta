from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from flask import current_app
from sqlalchemy import select, text

from extensions import db
from g2g import (
    G2GConflictError,
    G2GError,
    deliver_code,
    delivery_candidates,
    delivery_is_complete,
    delivery_status_value,
    get_delivery_status,
    resolve_delivery_id,
)
from models import (
    CancellationTombstone,
    DeliveryAttempt,
    Order,
    WebhookEvent,
)
from security import decrypt_text, encrypt_text
from services import (
    InvalidQuantityError,
    UnknownOfferError,
    as_utc,
    create_g2g_order,
    delivery_text,
    parse_event_time,
    revoke_order,
)

FULFILLMENT_EVENTS = {"order.api_delivery", "order_api_delivery"}
REVOCATION_EVENTS = {
    "order.cancelled",
    "order.canceled",
    "order.refunded",
    "order_cancelled",
    "order_canceled",
    "order_refunded",
}
DELIVERY_STATUS_EVENTS = {"order.delivery_status", "order_delivery_status"}


class WebhookPayloadError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class WebhookConflictError(WebhookPayloadError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=409)


@dataclass(frozen=True)
class ParsedWebhook:
    event_id: str
    event_type: str
    normalized_event: str
    event_happened_at: datetime
    order_id: str | None
    payload: dict[str, Any]
    body: dict[str, Any]
    payload_digest: str
    canonical_body: str


@dataclass(frozen=True)
class WebhookOutcome:
    response: dict[str, Any]
    status_code: int


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _nested(payload: dict[str, Any], *paths: tuple[str, ...]):
    for path in paths:
        value: Any = payload
        for key in path:
            if not isinstance(value, dict) or key not in value:
                value = None
                break
            value = value[key]
        if value not in (None, ""):
            return value
    return None


def parse_webhook(body: Any) -> ParsedWebhook:
    if not isinstance(body, dict):
        raise WebhookPayloadError("invalid JSON payload")

    event_type = str(
        body.get("event_type") or body.get("event") or body.get("type") or ""
    ).strip()
    if not event_type:
        raise WebhookPayloadError("missing event_type")

    raw_payload = body.get("payload")
    if raw_payload is None:
        raw_payload = body.get("data")
    if raw_payload is None:
        raw_payload = body
    if not isinstance(raw_payload, dict):
        raise WebhookPayloadError("invalid payload")
    payload = raw_payload

    order_id = (
        str(
            _nested(
                payload,
                ("order_id",),
                ("order", "id"),
                ("order", "order_id"),
            )
            or ""
        ).strip()
        or None
    )

    normalized_event = event_type.lower().replace("-", "_")
    if (
        normalized_event
        in (FULFILLMENT_EVENTS | REVOCATION_EVENTS | DELIVERY_STATUS_EVENTS)
        and not order_id
    ):
        raise WebhookPayloadError("missing order_id")

    canonical = _canonical_json(body)
    payload_digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    event_id = str(body.get("id") or body.get("event_id") or "").strip()
    if not event_id:
        event_id = "derived-" + payload_digest

    happened_at = parse_event_time(
        body.get("event_happened_at")
        or body.get("created_at")
        or payload.get("event_happened_at")
        or payload.get("created_at")
    )
    return ParsedWebhook(
        event_id=event_id[:180],
        event_type=event_type[:120],
        normalized_event=normalized_event,
        event_happened_at=happened_at,
        order_id=order_id,
        payload=payload,
        body=body,
        payload_digest=payload_digest,
        canonical_body=canonical,
    )


def _advisory_lock(namespace: str, value: str) -> None:
    if db.session.get_bind().dialect.name != "postgresql":
        return
    raw = hashlib.sha256(f"{namespace}:{value}".encode()).digest()[:8]
    key = int.from_bytes(raw, byteorder="big", signed=True)
    db.session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": key},
    )


def _event_record(
    parsed: ParsedWebhook,
) -> tuple[WebhookEvent, bool, WebhookPayloadError | None]:
    existing = db.session.scalar(
        select(WebhookEvent).where(WebhookEvent.event_id == parsed.event_id)
    )
    if existing is not None:
        existing.attempts += 1
        if existing.payload_digest != parsed.payload_digest:
            error = WebhookConflictError("event_id was reused with a different payload")
            existing.status = "conflict"
            existing.last_error = str(error)
            existing.processed_at = datetime.now(timezone.utc)
            return existing, False, error
        return existing, False, None

    event = WebhookEvent(
        event_id=parsed.event_id,
        event_type=parsed.event_type,
        g2g_order_id=parsed.order_id,
        payload_digest=parsed.payload_digest,
        payload_ciphertext=encrypt_text(parsed.canonical_body),
        status="processing",
        attempts=1,
        event_happened_at=parsed.event_happened_at,
    )
    db.session.add(event)
    db.session.flush()
    return event, True, None


def _fulfillment_fields(parsed: ParsedWebhook) -> dict[str, Any]:
    payload = parsed.payload
    offer_id = str(
        _nested(
            payload,
            ("offer_id",),
            ("offer", "id"),
            ("product", "offer_id"),
        )
        or ""
    ).strip()
    buyer_id = (
        str(_nested(payload, ("buyer_id",), ("buyer", "id")) or "").strip() or None
    )
    seller_id = str(_nested(payload, ("seller_id",), ("seller", "id")) or "").strip()

    quantity_value = _nested(
        payload,
        ("purchased_qty",),
        ("purchased_quantity",),
        ("quantity",),
        ("order", "purchased_qty"),
    )
    if quantity_value in (None, ""):
        raise WebhookPayloadError("missing purchased_qty")
    try:
        quantity = int(quantity_value)
    except (TypeError, ValueError) as exc:
        raise WebhookPayloadError("invalid purchased_qty") from exc

    if not offer_id:
        raise WebhookPayloadError("missing offer_id")
    if current_app.config["G2G_REQUIRE_SELLER_MATCH"]:
        if not seller_id:
            raise WebhookPayloadError("missing seller_id")
        if seller_id != current_app.config["G2G_USER_ID"]:
            raise WebhookPayloadError("seller mismatch", status_code=403)

    candidates = delivery_candidates(payload)
    delivery_id = None
    if len(candidates) == 1:
        delivery_id = str(candidates[0]["delivery_id"]).strip()

    purchased_at = parse_event_time(
        parsed.body.get("event_happened_at")
        or payload.get("purchased_at")
        or payload.get("created_at")
    )
    identity = {
        "order_id": parsed.order_id,
        "offer_id": offer_id,
        "buyer_id": buyer_id,
        "seller_id": seller_id,
        "quantity": quantity,
    }
    return {
        **identity,
        "identity_digest": _digest(identity),
        "delivery_id": delivery_id,
        "purchased_at": purchased_at,
    }


def _record_tombstone(
    parsed: ParsedWebhook, event: WebhookEvent
) -> CancellationTombstone:
    if parsed.order_id is None:
        raise WebhookPayloadError("missing order_id")
    tombstone = db.session.scalar(
        select(CancellationTombstone).where(
            CancellationTombstone.g2g_order_id == parsed.order_id
        )
    )
    if tombstone is None:
        tombstone = CancellationTombstone(
            g2g_order_id=parsed.order_id,
            event_id=event.event_id,
            reason=parsed.event_type,
            payload_digest=parsed.payload_digest,
            event_happened_at=parsed.event_happened_at,
        )
        db.session.add(tombstone)
    else:
        tombstone.event_id = event.event_id
        tombstone.reason = parsed.event_type
        tombstone.payload_digest = parsed.payload_digest
        tombstone.event_happened_at = parsed.event_happened_at
    return tombstone


def _process_fulfillment(
    parsed: ParsedWebhook, event: WebhookEvent
) -> tuple[Order | None, dict[str, Any]]:
    if parsed.order_id is None:
        raise WebhookPayloadError("missing order_id")
    fields = _fulfillment_fields(parsed)

    tombstone = db.session.scalar(
        select(CancellationTombstone).where(
            CancellationTombstone.g2g_order_id == parsed.order_id
        )
    )
    if tombstone is not None:
        event.status = "processed"
        event.processed_at = datetime.now(timezone.utc)
        event.last_error = "order already cancelled or refunded"
        return None, {
            "ok": True,
            "tombstoned": True,
            "delivery_status": "revoked",
        }

    order = db.session.scalar(
        select(Order).where(Order.g2g_order_id == parsed.order_id)
    )
    created_new = order is None
    if order is None:
        order, _ = create_g2g_order(
            g2g_order_id=parsed.order_id,
            delivery_id=fields["delivery_id"],
            offer_id=fields["offer_id"],
            buyer_id=fields["buyer_id"],
            quantity=fields["quantity"],
            purchased_at=fields["purchased_at"],
            source_payload_digest=fields["identity_digest"],
            event_id=event.event_id,
        )
    else:
        if (
            order.source_payload_digest
            and order.source_payload_digest != fields["identity_digest"]
        ):
            raise WebhookConflictError(
                "order_id was reused with conflicting buyer, offer, seller, or quantity"
            )
        if not order.source_payload_digest:
            order.source_payload_digest = fields["identity_digest"]
        if fields["delivery_id"] and not order.g2g_delivery_id:
            order.g2g_delivery_id = fields["delivery_id"]
        order.last_event_id = event.event_id

    event.status = "processed"
    event.processed_at = datetime.now(timezone.utc)
    event.last_error = None
    return order, {
        "ok": True,
        "created_new": created_new,
        "delivery_status": order.delivery_status,
    }


def _process_delivery_status(
    parsed: ParsedWebhook, event: WebhookEvent
) -> dict[str, Any]:
    if parsed.order_id is None:
        raise WebhookPayloadError("missing order_id")
    order = db.session.scalar(
        select(Order).where(Order.g2g_order_id == parsed.order_id)
    )
    if order is not None:
        candidates = delivery_candidates(parsed.payload)
        if len(candidates) == 1:
            incoming_delivery_id = str(candidates[0]["delivery_id"])
            if order.g2g_delivery_id and incoming_delivery_id != order.g2g_delivery_id:
                raise WebhookConflictError(
                    "delivery-status event conflicts with the order delivery_id"
                )
            if not order.g2g_delivery_id:
                order.g2g_delivery_id = incoming_delivery_id
        order.last_delivery_check_at = datetime.now(timezone.utc)
        if delivery_is_complete(parsed.payload):
            order.delivery_status = "delivered"
            order.delivered_at = datetime.now(timezone.utc)
            order.next_delivery_attempt_at = None
            order.last_error = None
    event.status = "processed"
    event.processed_at = datetime.now(timezone.utc)
    return {
        "ok": True,
        "order_found": order is not None,
        "delivery_status": order.delivery_status if order else None,
    }


def ingest_webhook(parsed: ParsedWebhook) -> tuple[dict[str, Any], int | None]:
    """Persist and apply one event.

    Returns ``(response, order_database_id)``. The caller performs external
    delivery only after this transaction commits.
    """

    error: WebhookPayloadError | None = None
    response: dict[str, Any] = {}
    order_database_id: int | None = None

    with db.session.begin():
        _advisory_lock("event", parsed.event_id)
        if parsed.order_id:
            _advisory_lock("order", parsed.order_id)

        event, created, event_error = _event_record(parsed)
        if event_error is not None:
            error = event_error
        elif not created and event.status in {
            "processed",
            "ignored",
        }:
            order = (
                db.session.scalar(
                    select(Order).where(Order.g2g_order_id == parsed.order_id)
                )
                if parsed.order_id
                else None
            )
            order_database_id = order.id if order else None
            response = {
                "ok": True,
                "duplicate": True,
                "event_status": event.status,
                "delivery_status": order.delivery_status if order else None,
            }
        else:
            try:
                event.status = "processing"
                if parsed.normalized_event in REVOCATION_EVENTS:
                    _record_tombstone(parsed, event)
                    revoked = revoke_order(
                        parsed.order_id or "",
                        reason=parsed.event_type,
                        commit=False,
                    )
                    event.status = "processed"
                    event.processed_at = datetime.now(timezone.utc)
                    response = {
                        "ok": True,
                        "revoked": revoked,
                        "tombstoned": True,
                    }
                elif parsed.normalized_event in FULFILLMENT_EVENTS:
                    order, response = _process_fulfillment(parsed, event)
                    order_database_id = order.id if order else None
                elif parsed.normalized_event in DELIVERY_STATUS_EVENTS:
                    response = _process_delivery_status(parsed, event)
                else:
                    event.status = "ignored"
                    event.processed_at = datetime.now(timezone.utc)
                    response = {
                        "ok": True,
                        "ignored": parsed.event_type,
                    }
            except (
                WebhookPayloadError,
                UnknownOfferError,
                InvalidQuantityError,
            ) as exc:
                if isinstance(exc, WebhookPayloadError):
                    error = exc
                else:
                    error = WebhookConflictError(str(exc))
                event.status = "conflict" if error.status_code == 409 else "failed"
                event.last_error = str(error)[:2000]
                event.processed_at = datetime.now(timezone.utc)

    if error is not None:
        raise error
    return response, order_database_id


def _retry_delay(attempt_number: int) -> timedelta:
    base = int(current_app.config["G2G_DELIVERY_RETRY_BASE_SECONDS"])
    seconds = min(3600, base * (2 ** max(0, attempt_number - 1)))
    return timedelta(seconds=seconds)


def _finish_delivery(
    *,
    order_id: int,
    attempt_id: int,
    success: bool,
    delivery_id: str | None,
    http_status: int | None,
    external_status: str | None,
    error: str | None,
) -> None:
    now = datetime.now(timezone.utc)
    with db.session.begin():
        order = db.session.get(Order, order_id)
        if order is None:
            return
        _advisory_lock("order", order.g2g_order_id)
        db.session.refresh(order)
        attempt = db.session.get(DeliveryAttempt, attempt_id)
        if delivery_id and not order.g2g_delivery_id:
            order.g2g_delivery_id = delivery_id
        order.last_delivery_check_at = now
        if success:
            order.delivery_status = "delivered"
            order.delivered_at = now
            order.next_delivery_attempt_at = None
            order.last_error = None
            if attempt is not None:
                attempt.status = "delivered"
        else:
            order.delivery_status = "failed"
            order.next_delivery_attempt_at = now + _retry_delay(order.delivery_attempts)
            order.last_error = (error or "delivery failed")[:2000]
            if attempt is not None:
                attempt.status = "failed"
                attempt.error = order.last_error
        if attempt is not None:
            attempt.http_status = http_status
            attempt.external_status = external_status[:120] if external_status else None
            attempt.finished_at = now


def attempt_delivery(order_id: int, *, force: bool = False) -> WebhookOutcome:
    now = datetime.now(timezone.utc)
    raw_key = ""
    content = ""
    delivery_id: str | None = None
    g2g_order_id = ""
    offer_id = ""
    attempt_id = 0
    access_key_ciphertext = ""

    db.session.rollback()
    with db.session.begin():
        order = db.session.get(Order, order_id)
        if order is None:
            return WebhookOutcome({"error": "order not found"}, 404)
        _advisory_lock("order", order.g2g_order_id)
        db.session.refresh(order)

        if order.status != "active":
            return WebhookOutcome({"ok": True, "delivery_status": order.status}, 200)
        if order.delivery_status in {"delivered", "manual"}:
            return WebhookOutcome(
                {"ok": True, "delivery_status": order.delivery_status}, 200
            )

        stale_seconds = int(current_app.config["G2G_DELIVERY_STALE_SECONDS"])
        if (
            order.delivery_status == "delivering"
            and order.delivery_started_at is not None
            and now - as_utc(order.delivery_started_at)
            < timedelta(seconds=stale_seconds)
        ):
            return WebhookOutcome({"ok": True, "delivery_status": "delivering"}, 200)

        maximum = int(current_app.config["G2G_DELIVERY_MAX_ATTEMPTS"])
        if not force and order.delivery_attempts >= maximum:
            return WebhookOutcome(
                {
                    "error": "delivery retry limit reached",
                    "delivery_status": order.delivery_status,
                },
                502,
            )

        order.delivery_attempts += 1
        order.delivery_status = "delivering"
        order.delivery_started_at = now
        order.next_delivery_attempt_at = None
        order.last_error = None
        attempt = DeliveryAttempt(
            order_id=order.id,
            attempt_number=order.delivery_attempts,
            status="started",
        )
        db.session.add(attempt)
        db.session.flush()

        access_key_ciphertext = order.access_key_ciphertext
        delivery_id = order.g2g_delivery_id
        g2g_order_id = order.g2g_order_id
        offer_id = order.offer_id
        attempt_id = attempt.id

    try:
        raw_key = decrypt_text(access_key_ciphertext)
        webhook_payload: dict[str, Any] = {}
        try:
            order_for_delivery = db.session.get(Order, order_id)
            if order_for_delivery is None:
                raise RuntimeError("Order disappeared before delivery")
            content = delivery_text(order_for_delivery, raw_key)
            if not delivery_id:
                event = db.session.scalar(
                    select(WebhookEvent)
                    .where(WebhookEvent.g2g_order_id == g2g_order_id)
                    .order_by(WebhookEvent.id.desc())
                )
                if event is not None:
                    webhook_payload = json.loads(
                        decrypt_text(event.payload_ciphertext)
                    ).get("payload", {})
        finally:
            db.session.rollback()

        if not delivery_id:
            delivery_id = resolve_delivery_id(
                order_id=g2g_order_id,
                webhook_payload=webhook_payload,
                offer_id=offer_id,
            )

        result = deliver_code(
            order_id=g2g_order_id,
            delivery_id=delivery_id,
            content=content,
            reference_id=g2g_order_id,
        )
        external_status = delivery_status_value(result["data"])
        _finish_delivery(
            order_id=order_id,
            attempt_id=attempt_id,
            success=True,
            delivery_id=delivery_id,
            http_status=result["status_code"],
            external_status=external_status,
            error=None,
        )
        return WebhookOutcome({"ok": True, "delivery_status": "delivered"}, 200)
    except G2GConflictError as exc:
        db.session.rollback()
        try:
            if not delivery_id:
                raise G2GError("Cannot reconcile delivery without delivery_id")
            status_result = get_delivery_status(g2g_order_id, delivery_id)
            complete = delivery_is_complete(status_result["data"])
            status_value = delivery_status_value(status_result["data"])
            _finish_delivery(
                order_id=order_id,
                attempt_id=attempt_id,
                success=complete,
                delivery_id=delivery_id,
                http_status=status_result["status_code"],
                external_status=status_value,
                error=None if complete else str(exc),
            )
            if complete:
                return WebhookOutcome(
                    {
                        "ok": True,
                        "delivery_status": "delivered",
                        "reconciled": True,
                    },
                    200,
                )
            return WebhookOutcome(
                {
                    "error": "G2G delivery conflict was not confirmed as delivered",
                    "delivery_status": status_value,
                },
                502,
            )
        except G2GError as reconcile_error:
            _finish_delivery(
                order_id=order_id,
                attempt_id=attempt_id,
                success=False,
                delivery_id=delivery_id,
                http_status=reconcile_error.status_code or exc.status_code,
                external_status=None,
                error=str(reconcile_error),
            )
            return WebhookOutcome({"error": str(reconcile_error)}, 502)
    except G2GError as exc:
        db.session.rollback()
        _finish_delivery(
            order_id=order_id,
            attempt_id=attempt_id,
            success=False,
            delivery_id=delivery_id,
            http_status=exc.status_code,
            external_status=None,
            error=str(exc),
        )
        return WebhookOutcome({"error": str(exc)}, 502)
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Unexpected G2G delivery failure")
        _finish_delivery(
            order_id=order_id,
            attempt_id=attempt_id,
            success=False,
            delivery_id=delivery_id,
            http_status=None,
            external_status=None,
            error=f"Unexpected delivery failure: {exc}",
        )
        return WebhookOutcome({"error": "internal delivery error"}, 500)


def handle_webhook(body: Any) -> WebhookOutcome:
    parsed = parse_webhook(body)
    response, order_id = ingest_webhook(parsed)
    if order_id is not None and parsed.normalized_event in FULFILLMENT_EVENTS:
        delivery = attempt_delivery(order_id)
        merged = {**response, **delivery.response}
        return WebhookOutcome(merged, delivery.status_code)
    return WebhookOutcome(response, 200)


def retry_due_deliveries(*, limit: int = 50) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    stale = now - timedelta(
        seconds=int(current_app.config["G2G_DELIVERY_STALE_SECONDS"])
    )
    order_ids = db.session.scalars(
        select(Order.id)
        .where(
            Order.status == "active",
            Order.delivery_status.in_(["pending", "failed", "delivering"]),
            (
                (Order.next_delivery_attempt_at.is_(None))
                | (Order.next_delivery_attempt_at <= now)
            ),
            (
                (Order.delivery_status != "delivering")
                | (Order.delivery_started_at.is_(None))
                | (Order.delivery_started_at <= stale)
            ),
        )
        .order_by(Order.next_delivery_attempt_at.asc().nullsfirst())
        .limit(limit)
    ).all()
    db.session.rollback()

    delivered = 0
    failed = 0
    for order_id in order_ids:
        outcome = attempt_delivery(order_id)
        if outcome.status_code == 200:
            delivered += 1
        else:
            failed += 1
    return {"attempted": len(order_ids), "delivered": delivered, "failed": failed}


def reconcile_delivery(order_id: int) -> WebhookOutcome:
    order = db.session.get(Order, order_id)
    if order is None:
        return WebhookOutcome({"error": "order not found"}, 404)
    if not order.g2g_delivery_id:
        return WebhookOutcome({"error": "order has no delivery_id"}, 409)
    g2g_order_id = order.g2g_order_id
    delivery_id = order.g2g_delivery_id
    db.session.rollback()
    try:
        result = get_delivery_status(g2g_order_id, delivery_id)
    except G2GError as exc:
        return WebhookOutcome({"error": str(exc)}, 502)

    complete = delivery_is_complete(result["data"])
    status_value = delivery_status_value(result["data"])
    with db.session.begin():
        order = db.session.get(Order, order_id)
        if order:
            _advisory_lock("order", order.g2g_order_id)
            order.last_delivery_check_at = datetime.now(timezone.utc)
            if complete:
                order.delivery_status = "delivered"
                order.delivered_at = datetime.now(timezone.utc)
                order.next_delivery_attempt_at = None
                order.last_error = None
    return WebhookOutcome(
        {
            "ok": True,
            "complete": complete,
            "delivery_status": status_value,
        },
        200,
    )
