from __future__ import annotations

import os
from datetime import datetime, timezone

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix

from config import build_config, configuration_errors
from extensions import db
from g2g import G2GError, deliver_code, verify_webhook_signature
from models import Order
from services import (
    InvalidQuantityError,
    UnknownOfferError,
    active_order,
    create_or_get_g2g_order,
    delivery_text,
    parse_event_time,
    revoke_order,
    verify_buyer_key,
)
from totp import TOTPConfig, generate_totp, parse_totp_config


def _nested(payload: dict, *paths: tuple[str, ...]):
    for path in paths:
        value = payload
        for key in path:
            if not isinstance(value, dict) or key not in value:
                value = None
                break
            value = value[key]
        if value not in (None, ""):
            return value
    return None


def _client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(build_config())
    if test_config:
        app.config.update(test_config)

    if app.config.get("TESTING"):
        app.config["SESSION_COOKIE_SECURE"] = False

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    db.init_app(app)

    setup_errors = configuration_errors(app.config)
    try:
        totp_config = parse_totp_config(
            app.config.get("TOTP_SECRET", ""),
            app.config.get("TOTP_LABEL", "Software Account"),
            app.config.get("TOTP_ISSUER", "Software"),
        )
    except ValueError as exc:
        totp_config = None
        setup_errors.append(str(exc))

    app.extensions["totp_config"] = totp_config
    app.extensions["setup_errors"] = setup_errors

    with app.app_context():
        db.create_all()

    @app.after_request
    def add_security_headers(response):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers[
            "Permissions-Policy"
        ] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'none'; "
            "form-action 'self'; "
            "object-src 'none'"
        )
        if request.is_secure:
            response.headers[
                "Strict-Transport-Security"
            ] = "max-age=31536000; includeSubDomains"
        return response

    @app.get("/health")
    def health():
        database_ok = True
        try:
            db.session.execute(text("SELECT 1"))
        except Exception:
            database_ok = False
        return jsonify(
            status="ok" if database_ok else "degraded",
            configured=not bool(app.extensions["setup_errors"]),
            database=database_ok,
            g2g_enabled=bool(app.config["G2G_INTEGRATION_ENABLED"]),
        ), (200 if database_ok else 503)

    @app.get("/")
    def index():
        errors = app.extensions["setup_errors"]
        if errors:
            return render_template("setup_error.html", errors=errors), 503

        order = None
        order_id = session.get("order_id")
        if isinstance(order_id, int):
            order = active_order(order_id)
            if order is None:
                session.clear()

        totp: TOTPConfig = app.extensions["totp_config"]
        return render_template(
            "index.html",
            order=order,
            label=totp.label,
            issuer=totp.issuer,
            period=totp.period,
            provider=app.config["SOFTWARE_PROVIDER"],
            login_email=app.config["SOFTWARE_LOGIN_EMAIL"],
        )

    @app.post("/unlock")
    def unlock():
        if app.extensions["setup_errors"]:
            return redirect(url_for("index"))

        raw_key = request.form.get("access_key", "").strip()
        totp: TOTPConfig | None = app.extensions["totp_config"]
        label = totp.label if totp else "Software Account"
        issuer = totp.issuer if totp else app.config["TOTP_ISSUER"]
        period = totp.period if totp else 30

        if not 10 <= len(raw_key) <= 200:
            return render_template(
                "index.html",
                order=None,
                label=label,
                issuer=issuer,
                period=period,
                provider=app.config["SOFTWARE_PROVIDER"],
                login_email=app.config["SOFTWARE_LOGIN_EMAIL"],
                error="Enter the complete access key supplied with your order.",
            ), 400

        try:
            order = verify_buyer_key(
                raw_key,
                ip_address=_client_ip(),
                user_agent=request.headers.get("User-Agent", ""),
            )
        except PermissionError as exc:
            return render_template(
                "index.html",
                order=None,
                label=label,
                issuer=issuer,
                period=period,
                provider=app.config["SOFTWARE_PROVIDER"],
                login_email=app.config["SOFTWARE_LOGIN_EMAIL"],
                error=str(exc),
            ), 403

        session.clear()
        session.permanent = True
        session["order_id"] = int(order.id)
        return redirect(url_for("index"))

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("index"))

    @app.get("/api/code")
    def code_api():
        if app.extensions["setup_errors"]:
            return jsonify(error="The portal is not configured"), 503

        order_id = session.get("order_id")
        if not isinstance(order_id, int):
            return jsonify(error="Enter your access key first"), 401

        order = active_order(order_id)
        if order is None:
            session.clear()
            return jsonify(error="Your access has expired or was revoked"), 403

        totp: TOTPConfig = app.extensions["totp_config"]
        code, remaining = generate_totp(totp)
        return jsonify(
            code=code,
            remaining=remaining,
            period=totp.period,
            label=totp.label,
            issuer=totp.issuer,
            server_time=int(datetime.now(timezone.utc).timestamp()),
            expires_at=order.expires_at.isoformat(),
            product_name=order.product_name,
        )

    @app.post("/webhooks/g2g")
    def g2g_webhook():
        if not app.config["G2G_INTEGRATION_ENABLED"]:
            return jsonify(error="G2G integration is disabled"), 503

        valid, reason = verify_webhook_signature(request.headers)
        if not valid:
            app.logger.warning("Rejected G2G webhook: %s", reason)
            return jsonify(error="invalid signature"), 401

        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify(error="invalid JSON payload"), 400

        event_type = str(
            body.get("event_type")
            or body.get("event")
            or body.get("type")
            or ""
        ).strip()
        payload = body.get("payload") or body.get("data") or body
        if not isinstance(payload, dict):
            return jsonify(error="invalid payload"), 400

        order_id = str(
            _nested(
                payload,
                ("order_id",),
                ("order", "id"),
                ("order", "order_id"),
            )
            or ""
        ).strip()
        if not order_id:
            return jsonify(error="missing order_id"), 400

        normalized_event = event_type.lower().replace("-", "_")
        if normalized_event in {
            "order.cancelled",
            "order.canceled",
            "order.refunded",
            "order_cancelled",
            "order_canceled",
            "order_refunded",
        }:
            revoked = revoke_order(order_id, reason=event_type)
            return jsonify(ok=True, revoked=revoked)

        if normalized_event not in {"order.api_delivery", "order_api_delivery"}:
            return jsonify(ok=True, ignored=event_type)

        offer_id = str(
            _nested(
                payload,
                ("offer_id",),
                ("offer", "id"),
                ("product", "offer_id"),
            )
            or ""
        ).strip()
        delivery_id = str(
            _nested(
                payload,
                ("delivery_id",),
                ("delivery", "id"),
            )
            or ""
        ).strip()
        buyer_id = str(
            _nested(
                payload,
                ("buyer_id",),
                ("buyer", "id"),
            )
            or ""
        ).strip() or None
        seller_id = str(
            _nested(
                payload,
                ("seller_id",),
                ("seller", "id"),
            )
            or ""
        ).strip()

        try:
            quantity = int(
                _nested(payload, ("quantity",), ("purchased_quantity",)) or 1
            )
        except (TypeError, ValueError):
            return jsonify(error="invalid quantity"), 400

        if (
            app.config["G2G_REQUIRE_SELLER_MATCH"]
            and seller_id != app.config["G2G_USER_ID"]
        ):
            return jsonify(error="seller mismatch"), 403
        if not offer_id or not delivery_id:
            return jsonify(error="missing offer_id or delivery_id"), 400

        purchased_at = parse_event_time(
            body.get("event_happened_at")
            or payload.get("purchased_at")
            or payload.get("created_at")
        )

        try:
            order, raw_key, created_new = create_or_get_g2g_order(
                g2g_order_id=order_id,
                delivery_id=delivery_id,
                offer_id=offer_id,
                buyer_id=buyer_id,
                quantity=quantity,
                purchased_at=purchased_at,
            )

            if order.delivery_status != "delivered":
                content = delivery_text(order, raw_key)
                deliver_code(
                    order_id=order.g2g_order_id,
                    delivery_id=order.g2g_delivery_id or delivery_id,
                    content=content,
                    reference_id=order.g2g_order_id,
                )
                order.delivery_status = "delivered"
                order.last_error = None
                db.session.commit()

            return jsonify(
                ok=True,
                created_new=created_new,
                delivery_status=order.delivery_status,
            )
        except (UnknownOfferError, InvalidQuantityError) as exc:
            app.logger.warning("Cannot fulfill G2G order %s: %s", order_id, exc)
            return jsonify(error=str(exc)), 409
        except G2GError as exc:
            order = db.session.scalar(
                db.select(Order).where(Order.g2g_order_id == order_id)
            )
            if order:
                order.delivery_status = "failed"
                order.last_error = str(exc)[:2000]
                db.session.commit()
            app.logger.exception("G2G delivery failed")
            return jsonify(error=str(exc)), 502
        except Exception:
            db.session.rollback()
            app.logger.exception("Unexpected G2G fulfillment failure")
            return jsonify(error="internal error"), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False,
    )
