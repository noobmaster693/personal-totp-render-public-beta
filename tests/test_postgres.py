from __future__ import annotations

import os
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from app import create_app
from config import normalize_database_url
from extensions import db
from models import DeliveryAttempt, Order, WebhookEvent
from tests.helpers import app_config, fixture, signed_headers


@unittest.skipUnless(
    os.getenv("TEST_DATABASE_URL"),
    "TEST_DATABASE_URL is required for PostgreSQL integration tests",
)
class PostgreSQLWebhookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        url = normalize_database_url(os.environ["TEST_DATABASE_URL"])
        cls.app = create_app(app_config(url, g2g_enabled=True))

    def setUp(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_concurrent_duplicate_webhooks_are_serialized(self):
        payload = fixture(
            "order_api_delivery.json",
            order_id="POSTGRES-CONCURRENT-1",
            event_id="postgres-concurrent-event",
        )
        headers = signed_headers(self.app)

        def deliver_once(**_kwargs):
            time.sleep(0.15)
            return {
                "data": {"delivery_status": "delivered"},
                "status_code": 200,
            }

        def post_webhook():
            with self.app.test_client() as client:
                response = client.post(
                    "/webhooks/g2g",
                    json=payload,
                    headers=headers,
                )
                return response.status_code, response.get_json()

        with (
            patch(
                "webhook_service.resolve_delivery_id",
                return_value="D-POSTGRES-CONCURRENT",
            ),
            patch(
                "webhook_service.deliver_code",
                side_effect=deliver_once,
            ) as deliver_mock,
            ThreadPoolExecutor(max_workers=2) as executor,
        ):
            results = list(executor.map(lambda _: post_webhook(), range(2)))

        self.assertEqual([status for status, _ in results], [200, 200])
        with self.app.app_context():
            self.assertEqual(db.session.query(Order).count(), 1)
            self.assertEqual(db.session.query(WebhookEvent).count(), 1)
            self.assertEqual(db.session.query(DeliveryAttempt).count(), 1)
            order = db.session.scalar(db.select(Order))
            event = db.session.scalar(db.select(WebhookEvent))
            self.assertEqual(order.delivery_status, "delivered")
            self.assertEqual(event.attempts, 2)
        deliver_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
