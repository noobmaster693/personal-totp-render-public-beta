from __future__ import annotations

from datetime import datetime, timezone

from extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    g2g_order_id = db.Column(db.String(160), unique=True, nullable=False, index=True)
    g2g_delivery_id = db.Column(db.String(160), nullable=True, index=True)
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
    source_payload_digest = db.Column(db.String(64), nullable=True)
    last_event_id = db.Column(db.String(180), nullable=True)
    delivery_attempts = db.Column(db.Integer, nullable=False, default=0)
    delivery_started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    next_delivery_attempt_at = db.Column(
        db.DateTime(timezone=True), nullable=True, index=True
    )
    delivered_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_delivery_check_at = db.Column(db.DateTime(timezone=True), nullable=True)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
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


class BuyerSession(db.Model):
    __tablename__ = "buyer_sessions"

    id = db.Column(db.Integer, primary_key=True)
    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True
    )
    ip_address = db.Column(db.String(80), nullable=False, index=True)
    user_agent = db.Column(db.Text, nullable=False, default="")
    timezone_hint = db.Column(db.String(120), nullable=True)
    language_hint = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    last_seen_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    revoke_reason = db.Column(db.String(240), nullable=True)


class WebhookEvent(db.Model):
    __tablename__ = "webhook_events"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(180), unique=True, nullable=False, index=True)
    event_type = db.Column(db.String(120), nullable=False, index=True)
    g2g_order_id = db.Column(db.String(160), nullable=True, index=True)
    payload_digest = db.Column(db.String(64), nullable=False)
    payload_ciphertext = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(32), nullable=False, default="received", index=True)
    attempts = db.Column(db.Integer, nullable=False, default=1)
    last_error = db.Column(db.Text, nullable=True)
    event_happened_at = db.Column(db.DateTime(timezone=True), nullable=False)
    received_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    processed_at = db.Column(db.DateTime(timezone=True), nullable=True)


class CancellationTombstone(db.Model):
    __tablename__ = "cancellation_tombstones"

    id = db.Column(db.Integer, primary_key=True)
    g2g_order_id = db.Column(db.String(160), unique=True, nullable=False, index=True)
    event_id = db.Column(db.String(180), nullable=False)
    reason = db.Column(db.String(120), nullable=False)
    payload_digest = db.Column(db.String(64), nullable=False)
    event_happened_at = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class DeliveryAttempt(db.Model):
    __tablename__ = "delivery_attempts"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True
    )
    attempt_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(32), nullable=False, index=True)
    http_status = db.Column(db.Integer, nullable=True)
    external_status = db.Column(db.String(120), nullable=True)
    error = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)


class PortalSettings(db.Model):
    __tablename__ = "portal_settings"

    id = db.Column(db.Integer, primary_key=True)
    provider_ciphertext = db.Column(db.Text, nullable=True)
    login_email_ciphertext = db.Column(db.Text, nullable=True)
    login_password_ciphertext = db.Column(db.Text, nullable=True)
    totp_secret_ciphertext = db.Column(db.Text, nullable=True)
    totp_label = db.Column(db.String(240), nullable=True)
    totp_issuer = db.Column(db.String(240), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class AdminAudit(db.Model):
    __tablename__ = "admin_audit"

    id = db.Column(db.Integer, primary_key=True)
    actor = db.Column(db.String(160), nullable=False)
    action = db.Column(db.String(120), nullable=False, index=True)
    target_type = db.Column(db.String(80), nullable=True)
    target_id = db.Column(db.String(180), nullable=True)
    ip_address = db.Column(db.String(80), nullable=False)
    user_agent = db.Column(db.Text, nullable=False, default="")
    details_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )
