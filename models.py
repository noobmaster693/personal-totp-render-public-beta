from __future__ import annotations

from datetime import datetime, timezone

from extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    g2g_order_id = db.Column(db.String(160), unique=True, nullable=False, index=True)
    g2g_delivery_id = db.Column(db.String(160), nullable=True)
    offer_id = db.Column(db.String(160), nullable=False, index=True)
    buyer_id = db.Column(db.String(160), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    product_name = db.Column(db.String(240), nullable=False)
    purchased_at = db.Column(db.DateTime(timezone=True), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    status = db.Column(db.String(32), nullable=False, default="active", index=True)
    delivery_status = db.Column(
        db.String(32), nullable=False, default="pending", index=True
    )
    access_key_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    access_key_ciphertext = db.Column(db.Text, nullable=False)
    last_error = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class AccessAttempt(db.Model):
    __tablename__ = "access_attempts"

    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(80), nullable=False, index=True)
    user_agent = db.Column(db.Text, nullable=False, default="")
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)
    result = db.Column(db.String(64), nullable=False, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )
