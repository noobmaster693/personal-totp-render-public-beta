from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app import create_app
from extensions import db
from localization import ENGLISH, LANGUAGE_OPTIONS, TRANSLATION_OVERRIDES
from models import BuyerSession, Order
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

    def test_language_is_auto_detected_and_can_be_changed(self):
        response = self.client.get(
            "/",
            headers={"Accept-Language": "en;q=0.2, fr-FR;q=0.9"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<html lang="fr" dir="ltr">', response.data)
        self.assertIn(
            "Saisissez votre clé d’accès".encode(),
            response.data,
        )
        self.assertEqual(response.data.count(b"<option value="), len(LANGUAGE_OPTIONS))

        response = self.client.post(
            "/language",
            data={"language": "ja"},
            headers={"Accept-Language": "fr"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<html lang="ja" dir="ltr">', response.data)
        self.assertIn("アクセスキーを入力".encode(), response.data)
        with self.client.session_transaction() as browser_session:
            self.assertEqual(browser_session["buyer_language"], "ja")

        self.assertEqual(
            self.client.post(
                "/language", data={"language": "not-supported"}
            ).status_code,
            400,
        )

    def test_chinese_variants_and_arabic_direction_are_supported(self):
        traditional = self.app.test_client().get(
            "/",
            headers={"Accept-Language": "zh-Hant-HK,zh;q=0.8"},
        )
        self.assertIn(b'<html lang="zh-tw" dir="ltr">', traditional.data)
        self.assertIn("請輸入存取金鑰".encode(), traditional.data)

        simplified = self.app.test_client().get(
            "/",
            headers={"Accept-Language": "zh-Hans"},
        )
        self.assertIn(b'<html lang="zh-cn" dir="ltr">', simplified.data)
        self.assertIn("请输入访问密钥".encode(), simplified.data)

        arabic = self.app.test_client().get(
            "/",
            headers={"Accept-Language": "ar"},
        )
        self.assertIn(b'<html lang="ar" dir="rtl">', arabic.data)
        self.assertIn("أدخل مفتاح الوصول".encode(), arabic.data)

    def test_selected_language_persists_through_unlock_and_localizes_errors(self):
        with self.app.app_context():
            order, raw_key = create_manual_order(
                order_id="LOCAL-LANGUAGE",
                product_name="International access",
                duration_seconds=3600,
            )
            order_id = order.id

        self.client.post("/language", data={"language": "es"})
        response = self.client.post(
            "/unlock",
            data={
                "access_key": raw_key,
                "language_hint": "es",
            },
            headers={"Accept-Language": "de"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<html lang="es" dir="ltr">', response.data)
        self.assertIn(b"Tu clave de compra ha sido aceptada", response.data)
        with self.app.app_context():
            buyer_session = db.session.scalar(
                db.select(BuyerSession).where(BuyerSession.order_id == order_id)
            )
            self.assertEqual(buyer_session.language_hint, "es")

        expired_client = self.app.test_client()
        expired_client.post("/language", data={"language": "fr"})
        with self.app.app_context():
            order = db.session.get(Order, order_id)
            order.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.session.commit()
        response = expired_client.post(
            "/unlock",
            data={"access_key": raw_key},
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cet abonnement a expiré".encode(), response.data)

    def test_every_advertised_language_has_a_complete_catalog(self):
        advertised = {code for code, _ in LANGUAGE_OPTIONS}
        self.assertEqual(advertised, {"en", *TRANSLATION_OVERRIDES})
        for language, translations in TRANSLATION_OVERRIDES.items():
            with self.subTest(language=language):
                self.assertEqual(set(translations), set(ENGLISH))

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
