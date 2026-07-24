"""Reliable webhooks, sessions, settings, and administration.

Revision ID: 20260724_0001
Revises:
Create Date: 2026-07-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260724_0001"
down_revision = None
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    return {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_indexes(table)
        if item.get("name")
    }


def _create_orders() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("g2g_order_id", sa.String(160), nullable=False, unique=True),
        sa.Column("g2g_delivery_id", sa.String(160), nullable=True),
        sa.Column("offer_id", sa.String(160), nullable=False),
        sa.Column("buyer_id", sa.String(160), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(240), nullable=False),
        sa.Column("purchased_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("delivery_status", sa.String(32), nullable=False),
        sa.Column("access_key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("access_key_ciphertext", sa.Text(), nullable=False),
        sa.Column("source_payload_digest", sa.String(64), nullable=True),
        sa.Column("last_event_id", sa.String(180), nullable=True),
        sa.Column(
            "delivery_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("delivery_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "next_delivery_attempt_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_delivery_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def _upgrade_legacy_orders() -> None:
    existing = _columns("orders")
    additions = {
        "source_payload_digest": sa.Column(
            "source_payload_digest", sa.String(64), nullable=True
        ),
        "last_event_id": sa.Column("last_event_id", sa.String(180), nullable=True),
        "delivery_attempts": sa.Column(
            "delivery_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        "delivery_started_at": sa.Column(
            "delivery_started_at", sa.DateTime(timezone=True), nullable=True
        ),
        "next_delivery_attempt_at": sa.Column(
            "next_delivery_attempt_at", sa.DateTime(timezone=True), nullable=True
        ),
        "delivered_at": sa.Column(
            "delivered_at", sa.DateTime(timezone=True), nullable=True
        ),
        "last_delivery_check_at": sa.Column(
            "last_delivery_check_at", sa.DateTime(timezone=True), nullable=True
        ),
        "revoked_at": sa.Column(
            "revoked_at", sa.DateTime(timezone=True), nullable=True
        ),
    }
    for name, column in additions.items():
        if name not in existing:
            op.add_column("orders", column)


def _create_access_attempts() -> None:
    op.create_table(
        "access_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ip_address", sa.String(80), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("result", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def _create_new_tables() -> None:
    tables = _tables()
    if "buyer_sessions" not in tables:
        op.create_table(
            "buyer_sessions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
            sa.Column(
                "order_id",
                sa.Integer(),
                sa.ForeignKey("orders.id"),
                nullable=False,
            ),
            sa.Column("ip_address", sa.String(80), nullable=False),
            sa.Column("user_agent", sa.Text(), nullable=False),
            sa.Column("timezone_hint", sa.String(120), nullable=True),
            sa.Column("language_hint", sa.String(120), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoke_reason", sa.String(240), nullable=True),
        )
    if "webhook_events" not in tables:
        op.create_table(
            "webhook_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("event_id", sa.String(180), nullable=False, unique=True),
            sa.Column("event_type", sa.String(120), nullable=False),
            sa.Column("g2g_order_id", sa.String(160), nullable=True),
            sa.Column("payload_digest", sa.String(64), nullable=False),
            sa.Column("payload_ciphertext", sa.Text(), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column(
                "attempts",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("1"),
            ),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("event_happened_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "cancellation_tombstones" not in tables:
        op.create_table(
            "cancellation_tombstones",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("g2g_order_id", sa.String(160), nullable=False, unique=True),
            sa.Column("event_id", sa.String(180), nullable=False),
            sa.Column("reason", sa.String(120), nullable=False),
            sa.Column("payload_digest", sa.String(64), nullable=False),
            sa.Column("event_happened_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "delivery_attempts" not in tables:
        op.create_table(
            "delivery_attempts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "order_id",
                sa.Integer(),
                sa.ForeignKey("orders.id"),
                nullable=False,
            ),
            sa.Column("attempt_number", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("http_status", sa.Integer(), nullable=True),
            sa.Column("external_status", sa.String(120), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "portal_settings" not in tables:
        op.create_table(
            "portal_settings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("provider_ciphertext", sa.Text(), nullable=True),
            sa.Column("login_email_ciphertext", sa.Text(), nullable=True),
            sa.Column("login_password_ciphertext", sa.Text(), nullable=True),
            sa.Column("totp_secret_ciphertext", sa.Text(), nullable=True),
            sa.Column("totp_label", sa.String(240), nullable=True),
            sa.Column("totp_issuer", sa.String(240), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "admin_audit" not in tables:
        op.create_table(
            "admin_audit",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("actor", sa.String(160), nullable=False),
            sa.Column("action", sa.String(120), nullable=False),
            sa.Column("target_type", sa.String(80), nullable=True),
            sa.Column("target_id", sa.String(180), nullable=True),
            sa.Column("ip_address", sa.String(80), nullable=False),
            sa.Column("user_agent", sa.Text(), nullable=False),
            sa.Column("details_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


INDEXES = {
    "orders": {
        "ix_orders_g2g_order_id": ["g2g_order_id"],
        "ix_orders_g2g_delivery_id": ["g2g_delivery_id"],
        "ix_orders_offer_id": ["offer_id"],
        "ix_orders_expires_at": ["expires_at"],
        "ix_orders_status": ["status"],
        "ix_orders_delivery_status": ["delivery_status"],
        "ix_orders_access_key_hash": ["access_key_hash"],
        "ix_orders_next_delivery_attempt_at": ["next_delivery_attempt_at"],
    },
    "access_attempts": {
        "ix_access_attempts_ip_address": ["ip_address"],
        "ix_access_attempts_result": ["result"],
        "ix_access_attempts_created_at": ["created_at"],
    },
    "buyer_sessions": {
        "ix_buyer_sessions_token_hash": ["token_hash"],
        "ix_buyer_sessions_order_id": ["order_id"],
        "ix_buyer_sessions_ip_address": ["ip_address"],
        "ix_buyer_sessions_last_seen_at": ["last_seen_at"],
        "ix_buyer_sessions_expires_at": ["expires_at"],
        "ix_buyer_sessions_revoked_at": ["revoked_at"],
    },
    "webhook_events": {
        "ix_webhook_events_event_id": ["event_id"],
        "ix_webhook_events_event_type": ["event_type"],
        "ix_webhook_events_g2g_order_id": ["g2g_order_id"],
        "ix_webhook_events_status": ["status"],
    },
    "cancellation_tombstones": {
        "ix_cancellation_tombstones_g2g_order_id": ["g2g_order_id"],
    },
    "delivery_attempts": {
        "ix_delivery_attempts_order_id": ["order_id"],
        "ix_delivery_attempts_status": ["status"],
    },
    "admin_audit": {
        "ix_admin_audit_action": ["action"],
        "ix_admin_audit_created_at": ["created_at"],
    },
}


def _create_indexes() -> None:
    tables = _tables()
    for table, indexes in INDEXES.items():
        if table not in tables:
            continue
        existing = _indexes(table)
        columns = _columns(table)
        for name, index_columns in indexes.items():
            if name not in existing and all(c in columns for c in index_columns):
                op.create_index(name, table, index_columns, unique=False)


def upgrade() -> None:
    tables = _tables()
    if "orders" not in tables:
        _create_orders()
    else:
        _upgrade_legacy_orders()

    if "access_attempts" not in _tables():
        _create_access_attempts()

    _create_new_tables()
    _create_indexes()


def downgrade() -> None:
    for table in (
        "admin_audit",
        "portal_settings",
        "delivery_attempts",
        "cancellation_tombstones",
        "webhook_events",
        "buyer_sessions",
    ):
        if table in _tables():
            op.drop_table(table)

    if "orders" in _tables():
        columns = _columns("orders")
        for name in (
            "revoked_at",
            "last_delivery_check_at",
            "delivered_at",
            "next_delivery_attempt_at",
            "delivery_started_at",
            "delivery_attempts",
            "last_event_id",
            "source_payload_digest",
        ):
            if name in columns:
                op.drop_column("orders", name)
