from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from extensions import db
from g2g import (
    G2GConflictError,
    G2GError,
    delivery_is_complete,
    verify_webhook_signature,
)
from models import (
    BuyerSession,
    CancellationTombstone,
    DeliveryAttempt,
    Order,
    WebhookEvent,
)
from security import decrypt_text
from tests.helpers import app_config, fixture, signed_headers

SUCCESSFUL_DELIVERY = {
    "data": {"delivery_status": "delivered"},
    "status_code": 200,
}


class WebhookTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "webhook.db"
        self.app = create_app(
            app_config(f"sqlite:///{database_path}", g2g_enabled=True)
        )
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.temp_dir.cleanup()

    def post(self, payload):
        return self.client.post(
            "/webhooks/g2g",
            json=payload,
            headers=signed_headers(self.app),
        )

    def test_documented_signature_uses_configured_identity_not_inbound_headers(self):
        headers = signed_headers(self.app)
        with self.app.app_context():
            valid, reason = verify_webhook_signature(headers)
            self.assertTrue(valid, reason)

            bad_headers = {
                **headers,
                "g2g-api-key": "someone-elses-key",
            }
            valid, reason = verify_webhook_signature(bad_headers)
            self.assertFalse(valid)
            self.assertEqual(reason, "unexpected API key")

    def test_reconciliation_ignores_generic_api_success_status(self):
        response = {
            "status": "success",
            "data": {
                "delivery_id": "D-PENDING",
                "delivery_status": "pending",
            },
        }
        self.assertFalse(delivery_is_complete(response))

    @patch(
        "webhook_service.deliver_code",
        return_value=SUCCESSFUL_DELIVERY,
    )
    @patch(
        "webhook_service.resolve_delivery_id",
        return_value="D1671612731000",
    )
    def test_documented_fixture_fulfills_without_root_delivery_id(
        self, resolve_mock, deliver_mock
    ):
        payload = fixture("order_api_delivery.json")
        payload["payload"]["additional_info_list"] = [
            {"label": "Account username", "value": "fixture-buyer-name"}
        ]
        response = self.post(payload)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))

        with self.app.app_context():
            order = db.session.scalar(db.select(Order))
            self.assertEqual(order.quantity, 1)
            self.assertEqual(order.buyer_username, "fixture-buyer-name")
            self.assertEqual(order.g2g_delivery_id, "D1671612731000")
            self.assertEqual(order.delivery_status, "delivered")
            event = db.session.scalar(db.select(WebhookEvent))
            self.assertEqual(event.status, "processed")
        resolve_mock.assert_called_once()
        deliver_mock.assert_called_once()

    @patch(
        "webhook_service.deliver_code",
        return_value=SUCCESSFUL_DELIVERY,
    )
    @patch(
        "webhook_service.resolve_delivery_id",
        return_value="D1671612731000",
    )
    def test_duplicate_event_reuses_one_order_and_one_delivery(
        self, _resolve_mock, deliver_mock
    ):
        payload = fixture("order_api_delivery.json")
        first = self.post(payload)
        second = self.post(payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.get_json()["duplicate"])

        with self.app.app_context():
            self.assertEqual(db.session.query(Order).count(), 1)
            self.assertEqual(db.session.query(WebhookEvent).count(), 1)
            self.assertEqual(db.session.query(DeliveryAttempt).count(), 1)
            event = db.session.scalar(db.select(WebhookEvent))
            self.assertEqual(event.attempts, 2)
        deliver_mock.assert_called_once()

    def test_cancellation_before_fulfillment_creates_tombstone(self):
        order_id = "CANCEL-FIRST-1"
        cancellation = fixture(
            "order_cancelled.json",
            order_id=order_id,
            event_id="cancel-first-event",
        )
        fulfillment = fixture(
            "order_api_delivery.json",
            order_id=order_id,
            event_id="late-fulfillment-event",
        )

        first = self.post(cancellation)
        second = self.post(fulfillment)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.get_json()["tombstoned"])

        with self.app.app_context():
            self.assertEqual(db.session.query(Order).count(), 0)
            tombstone = db.session.scalar(db.select(CancellationTombstone))
            self.assertEqual(tombstone.g2g_order_id, order_id)

    @patch(
        "webhook_service.deliver_code",
        return_value=SUCCESSFUL_DELIVERY,
    )
    @patch(
        "webhook_service.resolve_delivery_id",
        return_value="D-CANCEL-AFTER",
    )
    def test_cancellation_after_fulfillment_revokes_order_and_sessions(
        self, _resolve_mock, _deliver_mock
    ):
        order_id = "CANCEL-AFTER-1"
        fulfillment = fixture(
            "order_api_delivery.json",
            order_id=order_id,
            event_id="fulfillment-before-cancel",
        )
        self.assertEqual(self.post(fulfillment).status_code, 200)
        with self.app.app_context():
            order = db.session.scalar(db.select(Order))
            raw_key = decrypt_text(order.access_key_ciphertext)

        buyer = self.app.test_client()
        self.assertEqual(
            buyer.post("/unlock", data={"access_key": raw_key}).status_code,
            302,
        )
        cancellation = fixture(
            "order_cancelled.json",
            order_id=order_id,
            event_id="cancellation-after-fulfillment",
        )
        self.assertEqual(self.post(cancellation).status_code, 200)
        with self.app.app_context():
            order = db.session.scalar(db.select(Order))
            buyer_session = db.session.scalar(db.select(BuyerSession))
            self.assertEqual(order.status, "revoked")
            self.assertIsNotNone(buyer_session.revoked_at)
        self.assertEqual(buyer.get("/api/code").status_code, 403)

    @patch(
        "webhook_service.resolve_delivery_id",
        return_value="D-RETRY-1",
    )
    def test_failed_delivery_retries_on_duplicate_webhook(self, _resolve_mock):
        payload = fixture(
            "order_api_delivery.json",
            order_id="RETRY-ORDER-1",
            event_id="retry-event",
        )
        with patch(
            "webhook_service.deliver_code",
            side_effect=[
                G2GError("temporary outage", status_code=503),
                SUCCESSFUL_DELIVERY,
            ],
        ) as deliver_mock:
            first = self.post(payload)
            second = self.post(payload)

        self.assertEqual(first.status_code, 502)
        self.assertEqual(second.status_code, 200)
        with self.app.app_context():
            order = db.session.scalar(db.select(Order))
            self.assertEqual(order.delivery_status, "delivered")
            self.assertEqual(order.delivery_attempts, 2)
            self.assertEqual(db.session.query(DeliveryAttempt).count(), 2)
        self.assertEqual(deliver_mock.call_count, 2)

    @patch(
        "webhook_service.resolve_delivery_id",
        return_value="D-STATUS-EVENT",
    )
    @patch(
        "webhook_service.deliver_code",
        side_effect=G2GError("temporary outage", status_code=503),
    )
    def test_delivery_status_event_reconciles_a_failed_order(
        self, _deliver_mock, _resolve_mock
    ):
        order_id = "STATUS-EVENT-1"
        fulfillment = fixture(
            "order_api_delivery.json",
            order_id=order_id,
            event_id="status-event-fulfillment",
        )
        self.assertEqual(self.post(fulfillment).status_code, 502)

        status_event = fixture(
            "order_delivery_status.json",
            order_id=order_id,
            event_id="status-event-delivered",
        )
        status_event["payload"]["delivery_id"] = "D-STATUS-EVENT"
        response = self.post(status_event)
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            order = db.session.scalar(db.select(Order))
            self.assertEqual(order.delivery_status, "delivered")

    @patch(
        "webhook_service.resolve_delivery_id",
        return_value="D-CONFLICT-1",
    )
    @patch(
        "webhook_service.deliver_code",
        side_effect=G2GConflictError("duplicate", status_code=409, response_data={}),
    )
    @patch(
        "webhook_service.get_delivery_status",
        return_value={
            "data": {"delivery_status": "delivered"},
            "status_code": 200,
        },
    )
    def test_http_409_is_reconciled_before_marking_delivered(
        self, status_mock, _deliver_mock, _resolve_mock
    ):
        response = self.post(
            fixture(
                "order_api_delivery.json",
                order_id="RECONCILE-1",
                event_id="reconcile-event",
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["reconciled"])
        status_mock.assert_called_once_with("RECONCILE-1", "D-CONFLICT-1")

    @patch(
        "webhook_service.deliver_code",
        return_value=SUCCESSFUL_DELIVERY,
    )
    @patch(
        "webhook_service.resolve_delivery_id",
        return_value="D-EVENT-CONFLICT",
    )
    def test_reused_event_id_with_changed_payload_is_rejected(
        self, _resolve_mock, deliver_mock
    ):
        payload = fixture(
            "order_api_delivery.json",
            order_id="EVENT-CONFLICT-1",
            event_id="same-event-id",
        )
        self.assertEqual(self.post(payload).status_code, 200)
        changed = copy.deepcopy(payload)
        changed["payload"]["buyer_id"] = "different-buyer"
        response = self.post(changed)
        self.assertEqual(response.status_code, 409)
        deliver_mock.assert_called_once()

    @patch(
        "webhook_service.deliver_code",
        return_value=SUCCESSFUL_DELIVERY,
    )
    @patch(
        "webhook_service.resolve_delivery_id",
        return_value="D-ORDER-CONFLICT",
    )
    def test_order_id_with_conflicting_identity_is_rejected(
        self, _resolve_mock, _deliver_mock
    ):
        payload = fixture(
            "order_api_delivery.json",
            order_id="ORDER-CONFLICT-1",
            event_id="first-identity",
        )
        self.assertEqual(self.post(payload).status_code, 200)
        changed = copy.deepcopy(payload)
        changed["id"] = "second-identity"
        changed["payload"]["offer_id"] = "SECOND-OFFER"
        response = self.post(changed)
        self.assertEqual(response.status_code, 409)

    def test_missing_purchased_qty_is_recorded_as_failed(self):
        payload = fixture(
            "order_api_delivery.json",
            order_id="MISSING-QTY-1",
            event_id="missing-qty",
        )
        payload["payload"].pop("purchased_qty")
        response = self.post(payload)
        self.assertEqual(response.status_code, 400)
        with self.app.app_context():
            event = db.session.scalar(db.select(WebhookEvent))
            self.assertEqual(event.status, "failed")
            self.assertIn("purchased_qty", event.last_error)

    def test_account_configuration_failure_is_recorded_for_retry(self):
        self.app.config["SOFTWARE_LOGIN_PASSWORD"] = ""
        response = self.post(
            fixture(
                "order_api_delivery.json",
                order_id="CONFIG-FAILURE-1",
                event_id="config-failure-event",
            )
        )
        self.assertEqual(response.status_code, 500)
        with self.app.app_context():
            order = db.session.scalar(db.select(Order))
            attempt = db.session.scalar(db.select(DeliveryAttempt))
            self.assertEqual(order.delivery_status, "failed")
            self.assertEqual(attempt.status, "failed")
            self.assertIn("Missing account settings", order.last_error)

    def test_unknown_signed_event_is_acknowledged_and_ledgered(self):
        payload = {
            "id": "unknown-event",
            "event_happened_at": fixture("order_api_delivery.json")[
                "event_happened_at"
            ],
            "event_type": "order.created",
            "payload": {"order_id": "UNPAID-1"},
        }
        response = self.post(payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["ignored"], "order.created")
        with self.app.app_context():
            event = db.session.scalar(db.select(WebhookEvent))
            self.assertEqual(event.status, "ignored")


if __name__ == "__main__":
    unittest.main()
