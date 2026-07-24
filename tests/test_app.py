from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app import create_app
from extensions import db
from models import BuyerSession
from services import create_manual_order
from tests.helpers import app_config
from totp import TOTPConfig, generate_totp, verify_totp


class RFC6238Tests(unittest.TestCase):
    def test_sha1_vectors(self):
        config = TOTPConfig(
            secret="GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ",
            label="test",
            issuer="test",
            digits=8,
            period=30,
            algorithm="SHA1",
        )
        vectors = {
            59: "94287082",
            1111111109: "07081804",
            1111111111: "14050471",
            1234567890: "89005924",
            2000000000: "69279037",
            20000000000: "65353130",
        }
        for timestamp, expected in vectors.items():
            with self.subTest(timestamp=timestamp):
                code, _ = generate_totp(config, timestamp)
                self.assertEqual(code, expected)
                self.assertTrue(verify_totp(config, code, timestamp, window=0))


class PortalTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "test.db"
        self.app = create_app(
            app_config(f"sqlite:///{database_path}", g2g_enabled=False)
        )
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.temp_dir.cleanup()

    def test_code_is_not_public(self):
        response = self.client.get("/api/code")
        self.assertEqual(response.status_code, 401)

    def test_valid_key_creates_revocable_server_side_session(self):
        with self.app.app_context():
            order, raw_key = create_manual_order(
                order_id="LOCAL-1",
                product_name="One-hour test",
                duration_seconds=3600,
            )
            order_id = order.id

        response = self.client.post(
            "/unlock",
            data={
                "access_key": raw_key,
                "timezone_hint": "Europe/Paris",
                "language_hint": "fr-FR",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"One-hour test", response.data)

        response = self.client.get("/api/code")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["code"].isdigit())
        self.assertEqual(len(payload["code"]), 6)

        with self.app.app_context():
            buyer_session = db.session.scalar(
                db.select(BuyerSession).where(BuyerSession.order_id == order_id)
            )
            self.assertEqual(buyer_session.timezone_hint, "Europe/Paris")
            buyer_session.revoked_at = datetime.now(timezone.utc)
            db.session.commit()

        response = self.client.get("/api/code")
        self.assertEqual(response.status_code, 403)

    def test_expired_key_is_rejected(self):
        with self.app.app_context():
            order, raw_key = create_manual_order(
                order_id="LOCAL-2",
                product_name="Expired test",
                duration_seconds=3600,
            )
            order.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.session.commit()

        response = self.client.post("/unlock", data={"access_key": raw_key})
        self.assertEqual(response.status_code, 403)
        self.assertIn(b"expired", response.data.lower())

    def test_liveness_and_readiness_are_separate(self):
        live = self.client.get("/live")
        ready = self.client.get("/ready")
        self.assertEqual(live.status_code, 200)
        self.assertEqual(ready.status_code, 200)
        self.assertTrue(ready.get_json()["database"])
        self.assertTrue(ready.get_json()["migrations"])

    def test_readiness_fails_when_migration_metadata_is_missing(self):
        self.app.config["SKIP_MIGRATION_CHECK"] = False
        response = self.client.get("/ready")
        self.assertEqual(response.status_code, 503)
        payload = response.get_json()
        self.assertTrue(payload["database"])
        self.assertFalse(payload["migrations"])

    def test_webhook_is_disabled_by_default(self):
        response = self.client.post("/webhooks/g2g", json={})
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
