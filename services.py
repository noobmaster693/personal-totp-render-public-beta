from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from flask import current_app
from sqlalchemy import func, select

from extensions import db
from models import AccessAttempt, Order
from security import decrypt_text, encrypt_text, generate_access_key, hash_access_key


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


def ensure_order_state(order: Order) -> bool:
    now = datetime.now(timezone.utc)
    expires_at = as_utc(order.expires_at)
    if order.status == "active" and now >= expires_at:
        order.status = "expired"
        db.session.commit()
    return order.status == "active" and now < expires_at


def verify_buyer_key(
    raw_key: str, *, ip_address: str, user_agent: str
) -> Order:
    if is_rate_limited(ip_address):
        raise PermissionError("Too many failed attempts. Wait a few minutes.")

    key_hash = hash_access_key(raw_key)
    order = db.session.scalar(
        select(Order).where(Order.access_key_hash == key_hash)
    )

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


def active_order(order_id: int) -> Order | None:
    order = db.session.get(Order, order_id)
    if order is None:
        return None
    if not ensure_order_state(order):
        return None
    return order


def create_or_get_g2g_order(
    *,
    g2g_order_id: str,
    delivery_id: str | None,
    offer_id: str,
    buyer_id: str | None,
    quantity: int,
    purchased_at: datetime,
) -> tuple[Order, str, bool]:
    existing = db.session.scalar(
        select(Order).where(Order.g2g_order_id == g2g_order_id)
    )
    if existing:
        return existing, decrypt_text(existing.access_key_ciphertext), False

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
    expires_at = purchased_at + timedelta(
        seconds=int(product["duration_seconds"])
    )

    order = Order(
        g2g_order_id=g2g_order_id,
        g2g_delivery_id=delivery_id,
        offer_id=str(offer_id),
        buyer_id=buyer_id,
        quantity=quantity,
        product_name=str(product["name"]),
        purchased_at=purchased_at,
        expires_at=expires_at,
        status="active",
        delivery_status="pending",
        access_key_hash=hash_access_key(raw_key),
        access_key_ciphertext=encrypt_text(raw_key),
    )
    db.session.add(order)
    db.session.commit()
    return order, raw_key, True


def create_manual_order(
    *,
    order_id: str,
    product_name: str,
    duration_seconds: int,
) -> tuple[Order, str]:
    existing = db.session.scalar(
        select(Order).where(Order.g2g_order_id == order_id)
    )
    if existing:
        return existing, decrypt_text(existing.access_key_ciphertext)

    now = datetime.now(timezone.utc)
    raw_key = generate_access_key()
    order = Order(
        g2g_order_id=order_id,
        g2g_delivery_id="MANUAL",
        offer_id="MANUAL",
        buyer_id="MANUAL",
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
    provider = current_app.config["SOFTWARE_PROVIDER"]
    email = current_app.config["SOFTWARE_LOGIN_EMAIL"]
    password = current_app.config["SOFTWARE_LOGIN_PASSWORD"]
    portal = current_app.config["PUBLIC_BASE_URL"]
    return (
        f"Software account provider: {provider}\n"
        f"Login email: {email}\n"
        f"Password: {password}\n\n"
        f"2FA portal: {portal}\n"
        f"Temporary access key: {raw_key}\n\n"
        f"Product: {order.product_name}\n"
        f"Access begins: {as_utc(order.purchased_at).isoformat()}\n"
        f"Access expires: {as_utc(order.expires_at).isoformat()}\n\n"
        "Open the 2FA portal and enter the temporary access key whenever the "
        "software asks for an authenticator code. The key stops working at "
        "the expiration time."
    )


def revoke_order(g2g_order_id: str, reason: str = "") -> bool:
    order = db.session.scalar(
        select(Order).where(Order.g2g_order_id == g2g_order_id)
    )
    if order is None:
        return False
    order.status = "revoked"
    order.last_error = reason[:2000] or order.last_error
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
    db.session.commit()
    return len(orders)
