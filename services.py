from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from flask import current_app
from sqlalchemy import distinct, func, select

from extensions import db
from models import AccessAttempt, BuyerSession, Order, VisitorEvent
from security import (
    decrypt_text,
    encrypt_text,
    generate_access_key,
    generate_session_token,
    hash_access_key,
    hash_session_token,
)
from settings_service import get_account_settings


class UnknownOfferError(RuntimeError):
    pass


class InvalidQuantityError(RuntimeError):
    pass


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_event_time(value: Any) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)

    if isinstance(value, (int, float)) or (
        isinstance(value, str) and value.strip().isdigit()
    ):
        raw = int(value)
        if raw > 10_000_000_000:
            raw = raw / 1000
        try:
            return datetime.fromtimestamp(raw, tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            return datetime.now(timezone.utc)

    if isinstance(value, str):
        text = value.strip().replace("Z", "+00:00")
        try:
            return as_utc(datetime.fromisoformat(text))
        except ValueError:
            pass

    return datetime.now(timezone.utc)


def log_attempt(
    *,
    ip_address: str,
    user_agent: str,
    result: str,
    order: Order | None = None,
) -> None:
    db.session.add(
        AccessAttempt(
            ip_address=ip_address[:80],
            user_agent=user_agent[:1000],
            result=result,
            order_id=order.id if order else None,
        )
    )


def record_public_visit(*, ip_address: str, user_agent: str, path: str = "/") -> None:
    if not current_app.config.get("VISITOR_LOG_ENABLED", True):
        return
    db.session.add(
        VisitorEvent(
            ip_address=(ip_address or "unknown")[:80],
            path=(path or "/")[:240],
            user_agent=user_agent[:1000],
        )
    )
    db.session.commit()


def is_rate_limited(ip_address: str) -> bool:
    window = int(current_app.config["RATE_LIMIT_WINDOW_SECONDS"])
    maximum = int(current_app.config["RATE_LIMIT_ATTEMPTS"])
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=window)
    count = db.session.scalar(
        select(func.count(AccessAttempt.id)).where(
            AccessAttempt.ip_address == ip_address,
            AccessAttempt.created_at >= cutoff,
            AccessAttempt.result.in_(["invalid_key", "revoked", "expired", "inactive"]),
        )
    )
    return int(count or 0) >= maximum


def ensure_order_state(order: Order, *, commit: bool = True) -> bool:
    now = datetime.now(timezone.utc)
    expires_at = as_utc(order.expires_at)
    if order.status == "active" and now >= expires_at:
        order.status = "expired"
        revoke_buyer_sessions(order.id, reason="order expired", commit=False)
        if commit:
            db.session.commit()
    return order.status == "active" and now < expires_at


def verify_buyer_key(raw_key: str, *, ip_address: str, user_agent: str) -> Order:
    if is_rate_limited(ip_address):
        raise PermissionError("Too many failed attempts. Wait a few minutes.")

    key_hash = hash_access_key(raw_key)
    order = db.session.scalar(select(Order).where(Order.access_key_hash == key_hash))

    if order is None:
        log_attempt(
            ip_address=ip_address,
            user_agent=user_agent,
            result="invalid_key",
        )
        db.session.commit()
        raise PermissionError("Invalid access key.")

    if order.status == "revoked":
        log_attempt(
            ip_address=ip_address,
            user_agent=user_agent,
            result="revoked",
            order=order,
        )
        db.session.commit()
        raise PermissionError("This access key has been revoked.")

    if not ensure_order_state(order):
        log_attempt(
            ip_address=ip_address,
            user_agent=user_agent,
            result="expired",
            order=order,
        )
        db.session.commit()
        raise PermissionError("This subscription has expired.")

    log_attempt(
        ip_address=ip_address,
        user_agent=user_agent,
        result="success",
        order=order,
    )
    db.session.commit()
    return order


def _active_session_filter(now: datetime):
    return (
        BuyerSession.revoked_at.is_(None),
        BuyerSession.expires_at > now,
    )


def create_buyer_session(
    order: Order,
    *,
    ip_address: str,
    user_agent: str,
    timezone_hint: str = "",
    language_hint: str = "",
) -> tuple[BuyerSession, str]:
    now = datetime.now(timezone.utc)
    max_sessions = int(current_app.config.get("MAX_ACTIVE_SESSIONS_PER_ORDER", 0))
    max_ips = int(current_app.config.get("MAX_DISTINCT_IPS_PER_ORDER", 0))

    if max_sessions:
        active_count = db.session.scalar(
            select(func.count(BuyerSession.id)).where(
                BuyerSession.order_id == order.id,
                *_active_session_filter(now),
            )
        )
        if int(active_count or 0) >= max_sessions:
            raise PermissionError("This order has reached its active-session limit.")

    if max_ips:
        active_ips = db.session.scalar(
            select(func.count(distinct(BuyerSession.ip_address))).where(
                BuyerSession.order_id == order.id,
                *_active_session_filter(now),
            )
        )
        existing_ip = db.session.scalar(
            select(BuyerSession.id).where(
                BuyerSession.order_id == order.id,
                BuyerSession.ip_address == ip_address,
                *_active_session_filter(now),
            )
        )
        if int(active_ips or 0) >= max_ips and existing_ip is None:
            raise PermissionError("This order has reached its distinct-IP limit.")

    raw_token = generate_session_token()
    lifetime = current_app.permanent_session_lifetime
    expires_at = min(as_utc(order.expires_at), now + lifetime)
    buyer_session = BuyerSession(
        token_hash=hash_session_token(raw_token),
        order_id=order.id,
        ip_address=ip_address[:80],
        user_agent=user_agent[:1000],
        timezone_hint=timezone_hint[:120] or None,
        language_hint=language_hint[:120] or None,
        expires_at=expires_at,
    )
    db.session.add(buyer_session)
    db.session.commit()
    return buyer_session, raw_token


def active_buyer_session(raw_token: str) -> tuple[BuyerSession, Order] | None:
    if not raw_token:
        return None
    buyer_session = db.session.scalar(
        select(BuyerSession).where(
            BuyerSession.token_hash == hash_session_token(raw_token)
        )
    )
    if buyer_session is None or buyer_session.revoked_at is not None:
        return None

    now = datetime.now(timezone.utc)
    if now >= as_utc(buyer_session.expires_at):
        buyer_session.revoked_at = now
        buyer_session.revoke_reason = "session expired"
        db.session.commit()
        return None

    order = db.session.get(Order, buyer_session.order_id)
    if order is None or not ensure_order_state(order):
        return None

    if now - as_utc(buyer_session.last_seen_at) >= timedelta(seconds=30):
        buyer_session.last_seen_at = now
        db.session.commit()
    return buyer_session, order


def active_order(order_id: int) -> Order | None:
    """Compatibility helper used by management commands and older callers."""

    order = db.session.get(Order, order_id)
    if order is None or not ensure_order_state(order):
        return None
    return order


def create_g2g_order(
    *,
    g2g_order_id: str,
    delivery_id: str | None,
    offer_id: str,
    buyer_id: str | None,
    buyer_username: str | None,
    quantity: int,
    purchased_at: datetime,
    source_payload_digest: str,
    event_id: str,
) -> tuple[Order, str]:
    catalog = current_app.config["G2G_PRODUCTS"]
    product = catalog.get(str(offer_id))
    if not product:
        raise UnknownOfferError(
            f"No product in G2G_PRODUCTS_JSON matches offer_id={offer_id!r}"
        )

    if quantity < 1 or quantity > int(product.get("max_quantity", 1)):
        raise InvalidQuantityError(
            f"Quantity {quantity} is not permitted for offer {offer_id!r}"
        )

    raw_key = generate_access_key()
    purchased_at = as_utc(purchased_at)
    expires_at = purchased_at + timedelta(seconds=int(product["duration_seconds"]))
    order = Order(
        g2g_order_id=g2g_order_id,
        g2g_delivery_id=delivery_id,
        offer_id=str(offer_id),
        buyer_id=buyer_id,
        buyer_username=(buyer_username or "").strip()[:160] or None,
        quantity=quantity,
        product_name=str(product["name"]),
        purchased_at=purchased_at,
        expires_at=expires_at,
        status="active",
        delivery_status="pending",
        access_key_hash=hash_access_key(raw_key),
        access_key_ciphertext=encrypt_text(raw_key),
        source_payload_digest=source_payload_digest,
        last_event_id=event_id,
        next_delivery_attempt_at=datetime.now(timezone.utc),
    )
    db.session.add(order)
    db.session.flush()
    return order, raw_key


def create_or_get_g2g_order(
    *,
    g2g_order_id: str,
    delivery_id: str | None,
    offer_id: str,
    buyer_id: str | None,
    buyer_username: str | None,
    quantity: int,
    purchased_at: datetime,
    source_payload_digest: str = "",
    event_id: str = "",
) -> tuple[Order, str, bool]:
    existing = db.session.scalar(
        select(Order).where(Order.g2g_order_id == g2g_order_id)
    )
    if existing:
        return existing, decrypt_text(existing.access_key_ciphertext), False
    order, raw_key = create_g2g_order(
        g2g_order_id=g2g_order_id,
        delivery_id=delivery_id,
        offer_id=offer_id,
        buyer_id=buyer_id,
        buyer_username=buyer_username,
        quantity=quantity,
        purchased_at=purchased_at,
        source_payload_digest=source_payload_digest,
        event_id=event_id,
    )
    db.session.commit()
    return order, raw_key, True


def create_manual_order(
    *,
    order_id: str,
    product_name: str,
    duration_seconds: int,
    buyer_username: str | None = None,
    purchased_at: datetime | None = None,
    return_existing: bool = True,
) -> tuple[Order, str]:
    existing = db.session.scalar(select(Order).where(Order.g2g_order_id == order_id))
    if existing:
        if not return_existing:
            raise ValueError("That order reference already exists.")
        return existing, decrypt_text(existing.access_key_ciphertext)

    now = as_utc(purchased_at or datetime.now(timezone.utc))
    raw_key = generate_access_key()
    order = Order(
        g2g_order_id=order_id,
        g2g_delivery_id="MANUAL",
        offer_id="MANUAL",
        buyer_id="MANUAL",
        buyer_username=(buyer_username or "").strip()[:160] or None,
        quantity=1,
        product_name=product_name,
        purchased_at=now,
        expires_at=now + timedelta(seconds=duration_seconds),
        status="active",
        delivery_status="manual",
        access_key_hash=hash_access_key(raw_key),
        access_key_ciphertext=encrypt_text(raw_key),
    )
    db.session.add(order)
    db.session.commit()
    return order, raw_key


def delivery_text(order: Order, raw_key: str) -> str:
    account = get_account_settings()
    portal = current_app.config["PUBLIC_BASE_URL"]
    return (
        f"Software account provider: {account.provider}\n"
        f"Login email: {account.login_email}\n"
        f"Password: {account.login_password}\n\n"
        f"2FA portal: {portal}\n"
        f"Temporary access key: {raw_key}\n\n"
        f"Product: {order.product_name}\n"
        f"Access begins: {as_utc(order.purchased_at).isoformat()}\n"
        f"Access expires: {as_utc(order.expires_at).isoformat()}\n\n"
        "Open the 2FA portal and enter the temporary access key whenever the "
        "software asks for an authenticator code. The key stops working at "
        "the expiration time."
    )


def revoke_buyer_sessions(order_id: int, *, reason: str, commit: bool = True) -> int:
    now = datetime.now(timezone.utc)
    sessions = db.session.scalars(
        select(BuyerSession).where(
            BuyerSession.order_id == order_id,
            BuyerSession.revoked_at.is_(None),
        )
    ).all()
    for buyer_session in sessions:
        buyer_session.revoked_at = now
        buyer_session.revoke_reason = reason[:240]
    if commit:
        db.session.commit()
    return len(sessions)


def revoke_order(g2g_order_id: str, reason: str = "", *, commit: bool = True) -> bool:
    order = db.session.scalar(select(Order).where(Order.g2g_order_id == g2g_order_id))
    if order is None:
        return False
    now = datetime.now(timezone.utc)
    order.status = "revoked"
    order.revoked_at = now
    order.last_error = reason[:2000] or order.last_error
    revoke_buyer_sessions(order.id, reason=reason or "order revoked", commit=False)
    if commit:
        db.session.commit()
    return True


def revoke_session(session_id: int, *, reason: str) -> bool:
    buyer_session = db.session.get(BuyerSession, session_id)
    if buyer_session is None:
        return False
    buyer_session.revoked_at = datetime.now(timezone.utc)
    buyer_session.revoke_reason = reason[:240]
    db.session.commit()
    return True


def expire_due_orders() -> int:
    now = datetime.now(timezone.utc)
    orders = db.session.scalars(
        select(Order).where(
            Order.status == "active",
            Order.expires_at <= now,
        )
    ).all()
    for order in orders:
        order.status = "expired"
        revoke_buyer_sessions(order.id, reason="order expired", commit=False)
    db.session.commit()
    return len(orders)


def cleanup_operational_data(*, older_than_days: int = 90) -> dict[str, int]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    attempts = (
        db.session.query(AccessAttempt)
        .filter(AccessAttempt.created_at < cutoff)
        .delete(synchronize_session=False)
    )
    sessions = (
        db.session.query(BuyerSession)
        .filter(BuyerSession.expires_at < cutoff)
        .delete(synchronize_session=False)
    )
    visitor_events = (
        db.session.query(VisitorEvent)
        .filter(VisitorEvent.visited_at < cutoff)
        .delete(synchronize_session=False)
    )
    db.session.commit()
    return {
        "access_attempts": attempts,
        "buyer_sessions": sessions,
        "visitor_events": visitor_events,
    }
