from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app import create_app
from extensions import db
from models import AdminAudit, BuyerSession, Order, PortalSettings, VisitorEvent
from security import decrypt_text
from services import create_manual_order
from tests.helpers import (
    ADMIN_PASSWORD,
    ADMIN_TOTP_SECRET,
    app_config,
)
from totp import generate_totp, parse_totp_config


class AdminPortalTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "admin.db"
        self.app = create_app(app_config(f"sqlite:///{database_path}"))
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.temp_dir.cleanup()

    def csrf(self) -> str:
        with self.client.session_transaction() as browser_session:
            return browser_session["_csrf_token"]

    def login(self):
        response = self.client.get("/admin/login")
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            config = parse_totp_config(ADMIN_TOTP_SECRET, "Portal admin", "TOTP Portal")
            code, _ = generate_totp(config)
        response = self.client.post(
            "/admin/login",
            data={
                "_csrf_token": self.csrf(),
                "username": "admin",
                "password": ADMIN_PASSWORD,
                "totp_code": code,
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Shared-account access", response.data)

    def test_admin_requires_authentication_and_csrf(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.client.get("/admin/login")
        response = self.client.post(
            "/admin/login",
            data={
                "_csrf_token": "wrong",
                "username": "admin",
                "password": ADMIN_PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_totp_can_be_disabled_by_environment_flag(self):
        self.app.config["ADMIN_TOTP_REQUIRED"] = False
        self.app.config["ADMIN_TOTP_SECRET"] = "intentionally-invalid-and-ignored"
        response = self.client.get("/admin/login")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Administrator authenticator code", response.data)

        response = self.client.post(
            "/admin/login",
            data={
                "_csrf_token": self.csrf(),
                "username": "admin",
                "password": ADMIN_PASSWORD,
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Shared-account access", response.data)

    def test_admin_totp_is_required_when_enabled(self):
        self.client.get("/admin/login")
        response = self.client.post(
            "/admin/login",
            data={
                "_csrf_token": self.csrf(),
                "username": "admin",
                "password": ADMIN_PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_encrypted_account_settings_can_be_updated(self):
        self.login()
        response = self.client.post(
            "/admin/settings",
            data={
                "_csrf_token": self.csrf(),
                "provider": "Owned Software",
                "login_email": "shared@example.test",
                "login_password": "new-shared-password",
                "totp_secret": "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ",
                "totp_label": "Production shared account",
                "totp_issuer": "Owned Software",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Encrypted account settings updated", response.data)

        with self.app.app_context():
            settings = db.session.get(PortalSettings, 1)
            self.assertIsNotNone(settings)
            self.assertNotIn("shared@example.test", settings.login_email_ciphertext)
            self.assertNotIn("new-shared-password", settings.login_password_ciphertext)
            self.assertNotIn("GEZDGNBVGY3TQOJQ", settings.totp_secret_ciphertext)

    def test_admin_can_revoke_an_individual_buyer_session(self):
        with self.app.app_context():
            _, raw_key = create_manual_order(
                order_id="ADMIN-SESSION-1",
                product_name="Admin session test",
                duration_seconds=3600,
            )
        buyer = self.app.test_client()
        response = buyer.post("/unlock", data={"access_key": raw_key})
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            buyer_session = db.session.scalar(db.select(BuyerSession))
            buyer_session_id = buyer_session.id

        self.login()
        response = self.client.post(
            f"/admin/sessions/{buyer_session_id}/revoke",
            data={"_csrf_token": self.csrf()},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            buyer_session = db.session.get(BuyerSession, buyer_session_id)
            self.assertIsNotNone(buyer_session.revoked_at)
        self.assertEqual(buyer.get("/api/code").status_code, 403)

    def test_admin_can_create_and_explicitly_reveal_a_manual_key(self):
        self.login()
        response = self.client.get("/admin/orders/new")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Create a new key", response.data)

        response = self.client.post(
            "/admin/orders/new",
            data={
                "_csrf_token": self.csrf(),
                "order_reference": "MANUAL-CUSTOM-1",
                "buyer_username": "buyer-handle",
                "product_name": "Two-day software access",
                "duration_value": "2",
                "duration_unit": "days",
            },
        )
        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            order = db.session.scalar(
                db.select(Order).where(Order.g2g_order_id == "MANUAL-CUSTOM-1")
            )
            self.assertIsNotNone(order)
            self.assertEqual(order.buyer_username, "buyer-handle")
            self.assertEqual(
                int((order.expires_at - order.purchased_at).total_seconds()),
                2 * 86400,
            )
            raw_key = decrypt_text(order.access_key_ciphertext)
            order_id = order.id
            audit = db.session.scalar(
                db.select(AdminAudit).where(AdminAudit.action == "manual_order_created")
            )
            self.assertIsNotNone(audit)

        self.assertIn(raw_key.encode(), response.data)
        detail = self.client.get(f"/admin/orders/{order_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertNotIn(raw_key.encode(), detail.data)
        self.assertEqual(
            self.client.get(f"/admin/orders/{order_id}/key").status_code,
            405,
        )
        self.assertEqual(
            self.client.post(
                f"/admin/orders/{order_id}/key",
                data={"_csrf_token": "wrong"},
            ).status_code,
            400,
        )

        revealed = self.client.post(
            f"/admin/orders/{order_id}/key",
            data={"_csrf_token": self.csrf()},
        )
        self.assertEqual(revealed.status_code, 200)
        self.assertIn(raw_key.encode(), revealed.data)
        self.assertIn(b"This action was recorded", revealed.data)
        with self.app.app_context():
            reveal_audit = db.session.scalar(
                db.select(AdminAudit).where(AdminAudit.action == "access_key_revealed")
            )
            self.assertIsNotNone(reveal_audit)
            self.assertEqual(reveal_audit.target_id, str(order_id))

        buyer = self.app.test_client()
        unlock = buyer.post(
            "/unlock",
            data={"access_key": raw_key},
            environ_overrides={"REMOTE_ADDR": "203.0.113.25"},
            headers={"User-Agent": "ManualBuyer/1.0"},
        )
        self.assertEqual(unlock.status_code, 302)

        duplicate = self.client.post(
            "/admin/orders/new",
            data={
                "_csrf_token": self.csrf(),
                "order_reference": "MANUAL-CUSTOM-1",
                "buyer_username": "other-buyer",
                "product_name": "Duplicate",
                "duration_value": "1",
                "duration_unit": "days",
            },
        )
        self.assertEqual(duplicate.status_code, 400)
        with self.app.app_context():
            self.assertEqual(
                db.session.query(Order)
                .filter(Order.g2g_order_id == "MANUAL-CUSTOM-1")
                .count(),
                1,
            )

    def test_order_detail_shows_purchase_username_and_key_usage_ips(self):
        with self.app.app_context():
            order, raw_key = create_manual_order(
                order_id="DETAIL-ORDER-1",
                product_name="Order detail product",
                duration_seconds=3600,
                buyer_username="marketplace-user",
            )
            order_id = order.id

        buyer = self.app.test_client()
        response = buyer.post(
            "/unlock",
            data={
                "access_key": raw_key,
                "timezone_hint": "Europe/Paris",
                "language_hint": "en-GB",
            },
            environ_overrides={"REMOTE_ADDR": "198.51.100.44"},
            headers={"User-Agent": "DetailBrowser/2.0"},
        )
        self.assertEqual(response.status_code, 302)

        anonymous = self.app.test_client()
        self.assertEqual(
            anonymous.get(f"/admin/orders/{order_id}").status_code,
            302,
        )

        self.login()
        detail = self.client.get(f"/admin/orders/{order_id}")
        self.assertEqual(detail.status_code, 200)
        for expected in (
            b"marketplace-user",
            b"Purchase date",
            b"Expiration date",
            b"198.51.100.44",
            b"DetailBrowser/2.0",
            b"Europe/Paris",
            b"en-GB",
            b"success",
        ):
            self.assertIn(expected, detail.data)

    def test_public_visitor_report_only_logs_public_get_requests(self):
        visitor = self.app.test_client()
        request_options = {
            "environ_overrides": {"REMOTE_ADDR": "198.51.100.7"},
            "headers": {"User-Agent": "VisitorBrowser/3.0"},
        }
        self.assertEqual(visitor.get("/", **request_options).status_code, 200)
        self.assertEqual(visitor.get("/", **request_options).status_code, 200)
        self.assertEqual(visitor.head("/", **request_options).status_code, 200)
        self.assertEqual(visitor.get("/live", **request_options).status_code, 200)
        self.assertEqual(
            visitor.get("/admin/login", **request_options).status_code, 200
        )

        with self.app.app_context():
            visits = db.session.scalars(
                db.select(VisitorEvent).order_by(VisitorEvent.id)
            ).all()
            self.assertEqual(len(visits), 2)
            self.assertTrue(all(item.ip_address == "198.51.100.7" for item in visits))
            self.assertTrue(
                all(item.user_agent == "VisitorBrowser/3.0" for item in visits)
            )

        self.login()
        report = self.client.get("/admin/visitors")
        self.assertEqual(report.status_code, 200)
        self.assertIn(b"198.51.100.7", report.data)
        self.assertIn(b"VisitorBrowser/3.0", report.data)

        self.app.config["VISITOR_LOG_ENABLED"] = False
        self.assertEqual(visitor.get("/", **request_options).status_code, 200)
        with self.app.app_context():
            self.assertEqual(db.session.query(VisitorEvent).count(), 2)


if __name__ == "__main__":
    unittest.main()
