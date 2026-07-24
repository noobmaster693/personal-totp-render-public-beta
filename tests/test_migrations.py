from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[1]


def alembic_config() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    return config


def run_upgrade(database_url: str) -> None:
    with patch.dict(os.environ, {"DATABASE_URL": database_url}):
        command.upgrade(alembic_config(), "head")


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def database_url(self, name: str) -> str:
        return f"sqlite:///{Path(self.temp_dir.name) / name}"

    def test_fresh_database_upgrade_is_repeatable(self):
        url = self.database_url("fresh.db")
        run_upgrade(url)
        run_upgrade(url)

        engine = sa.create_engine(url)
        inspector = sa.inspect(engine)
        self.assertTrue(
            {
                "orders",
                "access_attempts",
                "buyer_sessions",
                "webhook_events",
                "cancellation_tombstones",
                "delivery_attempts",
                "portal_settings",
                "admin_audit",
                "visitor_events",
                "alembic_version",
            }.issubset(set(inspector.get_table_names()))
        )
        with engine.connect() as connection:
            version = connection.execute(
                sa.text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        self.assertEqual(version, "20260724_0002")
        order_columns = {item["name"] for item in inspector.get_columns("orders")}
        self.assertIn("buyer_username", order_columns)
        engine.dispose()

    def test_legacy_database_upgrade_preserves_orders_and_key_hashes(self):
        url = self.database_url("legacy.db")
        engine = sa.create_engine(url)
        metadata = sa.MetaData()
        orders = sa.Table(
            "orders",
            metadata,
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
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        sa.Table(
            "access_attempts",
            metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("ip_address", sa.String(80), nullable=False),
            sa.Column("user_agent", sa.Text(), nullable=False),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id")),
            sa.Column("result", sa.String(64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        metadata.create_all(engine)
        now = datetime.now(timezone.utc)
        with engine.begin() as connection:
            connection.execute(
                orders.insert().values(
                    id=7,
                    g2g_order_id="LEGACY-ORDER-7",
                    g2g_delivery_id="D-LEGACY",
                    offer_id="LEGACY-OFFER",
                    buyer_id="LEGACY-BUYER",
                    quantity=1,
                    product_name="Legacy access",
                    purchased_at=now,
                    expires_at=now,
                    status="active",
                    delivery_status="pending",
                    access_key_hash="a" * 64,
                    access_key_ciphertext="legacy-ciphertext",
                    last_error=None,
                    created_at=now,
                    updated_at=now,
                )
            )
        engine.dispose()

        run_upgrade(url)
        run_upgrade(url)

        engine = sa.create_engine(url)
        inspector = sa.inspect(engine)
        order_columns = {item["name"] for item in inspector.get_columns("orders")}
        self.assertIn("source_payload_digest", order_columns)
        self.assertIn("delivery_attempts", order_columns)
        self.assertIn("buyer_username", order_columns)
        self.assertIn("visitor_events", inspector.get_table_names())
        with engine.connect() as connection:
            row = (
                connection.execute(
                    sa.text(
                        "SELECT id, g2g_order_id, access_key_hash, "
                        "delivery_attempts FROM orders WHERE id = 7"
                    )
                )
                .mappings()
                .one()
            )
        self.assertEqual(row["g2g_order_id"], "LEGACY-ORDER-7")
        self.assertEqual(row["access_key_hash"], "a" * 64)
        self.assertEqual(row["delivery_attempts"], 0)
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
