"""Manual keys, order detail metadata, and public visitor events.

Revision ID: 20260724_0002
Revises: 20260724_0001
Create Date: 2026-07-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260724_0002"
down_revision = "20260724_0001"
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


def upgrade() -> None:
    if "buyer_username" not in _columns("orders"):
        op.add_column(
            "orders",
            sa.Column("buyer_username", sa.String(length=160), nullable=True),
        )
    if "ix_orders_buyer_username" not in _indexes("orders"):
        op.create_index(
            "ix_orders_buyer_username",
            "orders",
            ["buyer_username"],
            unique=False,
        )

    if "visitor_events" not in _tables():
        op.create_table(
            "visitor_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("ip_address", sa.String(length=80), nullable=False),
            sa.Column(
                "path",
                sa.String(length=240),
                nullable=False,
                server_default="/",
            ),
            sa.Column("user_agent", sa.Text(), nullable=False, server_default=""),
            sa.Column(
                "visited_at",
                sa.DateTime(timezone=True),
                nullable=False,
            ),
        )

    existing = _indexes("visitor_events")
    if "ix_visitor_events_ip_address" not in existing:
        op.create_index(
            "ix_visitor_events_ip_address",
            "visitor_events",
            ["ip_address"],
            unique=False,
        )
    if "ix_visitor_events_visited_at" not in existing:
        op.create_index(
            "ix_visitor_events_visited_at",
            "visitor_events",
            ["visited_at"],
            unique=False,
        )


def downgrade() -> None:
    if "visitor_events" in _tables():
        op.drop_table("visitor_events")
    if "buyer_username" in _columns("orders"):
        op.drop_column("orders", "buyer_username")
