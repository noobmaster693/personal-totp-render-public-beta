from __future__ import annotations

import os
from datetime import datetime, timezone

from cryptography.fernet import InvalidToken
from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.middleware.proxy_fix import ProxyFix

from admin import admin
from config import build_config, configuration_errors
from extensions import db
from g2g import verify_webhook_signature
from localization import (
    LANGUAGE_OPTIONS,
    direction_for,
    resolve_language,
    supported_language,
    translate_portal_error,
    translations_for,
)
from services import (
    active_buyer_session,
    create_buyer_session,
    record_public_visit,
    verify_buyer_key,
)
from settings_service import AccountSettings, get_account_settings
from totp import generate_totp
from webhook_service import (
    WebhookPayloadError,
    handle_webhook,
)


def _client_ip() -> str:
    # ProxyFix has already replaced REMOTE_ADDR using exactly one trusted
    # upstream proxy hop. Do not parse a user-controlled X-Forwarded-For again.
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
    app.register_blueprint(admin)
    app.extensions["setup_errors"] = configuration_errors(app.config)

    def buyer_language() -> str:
        return resolve_language(
            session.get("buyer_language"),
            request.headers.get("Accept-Language", ""),
        )

    def buyer_template_context(account: AccountSettings, *, order=None) -> dict:
        language = buyer_language()
        return {
            "order": order,
            "label": account.totp.label,
            "issuer": account.totp.issuer,
            "period": account.totp.period,
            "provider": account.provider,
            "login_email": account.login_email,
            "language": language,
            "direction": direction_for(language),
            "language_options": LANGUAGE_OPTIONS,
            "t": translations_for(language),
        }

    def account_or_errors() -> tuple[AccountSettings | None, list[str]]:
        errors = list(app.extensions["setup_errors"])
        try:
            account = get_account_settings()
        except InvalidToken:
            account = None
            errors.append("Encrypted account settings cannot be decrypted")
        except SQLAlchemyError:
            db.session.rollback()
            account = None
            errors.append("The database is unavailable or has not been migrated")
        except (TypeError, ValueError) as exc:
            account = None
            errors.append(str(exc))
        return account, errors

    def readiness() -> tuple[dict, int]:
        errors = list(app.extensions["setup_errors"])
        database_ok = True
        migration_ok = bool(app.config.get("SKIP_MIGRATION_CHECK"))
        migration_version = None
        try:
            db.session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            database_ok = False
            db.session.rollback()
            errors.append("Database connectivity check failed")

        if database_ok and not migration_ok:
            try:
                migration_version = db.session.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one_or_none()
                migration_ok = migration_version == app.config["MIGRATION_HEAD"]
                if not migration_ok:
                    errors.append("Database migrations are not at the expected head")
            except SQLAlchemyError:
                db.session.rollback()
                migration_ok = False
                errors.append("Database migration metadata is unavailable")

        if database_ok:
            try:
                get_account_settings()
            except InvalidToken:
                errors.append("Encrypted account settings cannot be decrypted")
            except SQLAlchemyError:
                db.session.rollback()
                errors.append("Account settings cannot be read")
            except (TypeError, ValueError) as exc:
                errors.append(str(exc))

        ready = database_ok and migration_ok and not errors
        return {
            "status": "ready" if ready else "not_ready",
            "configured": not bool(errors),
            "database": database_ok,
            "migrations": migration_ok,
            "migration_version": migration_version,
            "g2g_enabled": bool(app.config["G2G_INTEGRATION_ENABLED"]),
            "errors": errors,
        }, (200 if ready else 503)

    @app.after_request
    def add_security_headers(response):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
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
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    @app.get("/live")
    def live():
        return jsonify(status="alive")

    @app.get("/ready")
    def ready():
        payload, status = readiness()
        return jsonify(payload), status

    @app.get("/health")
    def health():
        payload, status = readiness()
        return jsonify(payload), status

    @app.get("/")
    def index():
        if request.method == "GET":
            try:
                record_public_visit(
                    ip_address=_client_ip(),
                    user_agent=request.headers.get("User-Agent", ""),
                    path=request.path,
                )
            except SQLAlchemyError:
                db.session.rollback()
                app.logger.warning(
                    "Could not record public visitor event", exc_info=True
                )

        account, errors = account_or_errors()
        if errors or account is None:
            return render_template("setup_error.html", errors=errors), 503

        order = None
        raw_session_token = session.get("buyer_session_token")
        if isinstance(raw_session_token, str):
            active = active_buyer_session(raw_session_token)
            if active is None:
                session.pop("buyer_session_token", None)
            else:
                _, order = active

        return render_template(
            "index.html",
            **buyer_template_context(account, order=order),
        )

    @app.post("/language")
    def set_language():
        language = supported_language(request.form.get("language"))
        if language is None:
            abort(400, "Unsupported language")
        session["buyer_language"] = language
        session.permanent = True
        return redirect(url_for("index"))

    @app.post("/unlock")
    def unlock():
        account, errors = account_or_errors()
        if errors or account is None:
            return redirect(url_for("index"))

        raw_key = request.form.get("access_key", "").strip()
        template_context = buyer_template_context(account)
        translations = template_context["t"]
        if not 10 <= len(raw_key) <= 200:
            return render_template(
                "index.html",
                **template_context,
                error=translations["complete_key_error"],
            ), 400

        try:
            order = verify_buyer_key(
                raw_key,
                ip_address=_client_ip(),
                user_agent=request.headers.get("User-Agent", ""),
            )
            _, raw_session_token = create_buyer_session(
                order,
                ip_address=_client_ip(),
                user_agent=request.headers.get("User-Agent", ""),
                timezone_hint=request.form.get("timezone_hint", ""),
                language_hint=request.form.get(
                    "language_hint",
                    request.headers.get("Accept-Language", ""),
                ),
            )
        except PermissionError as exc:
            return render_template(
                "index.html",
                **template_context,
                error=translate_portal_error(str(exc), translations),
            ), 403

        session.pop("buyer_session_token", None)
        session.permanent = True
        session["buyer_session_token"] = raw_session_token
        return redirect(url_for("index"))

    @app.post("/logout")
    def logout():
        session.pop("buyer_session_token", None)
        return redirect(url_for("index"))

    @app.get("/api/code")
    def code_api():
        translations = translations_for(buyer_language())
        account, errors = account_or_errors()
        if errors or account is None:
            return jsonify(error=translations["portal_not_configured"]), 503

        raw_session_token = session.get("buyer_session_token")
        if not isinstance(raw_session_token, str):
            return jsonify(error=translations["enter_key_first"]), 401

        active = active_buyer_session(raw_session_token)
        if active is None:
            session.pop("buyer_session_token", None)
            return jsonify(error=translations["access_ended"]), 403
        _, order = active

        code, remaining = generate_totp(account.totp)
        return jsonify(
            code=code,
            remaining=remaining,
            period=account.totp.period,
            label=account.totp.label,
            issuer=account.totp.issuer,
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
        try:
            outcome = handle_webhook(body)
        except WebhookPayloadError as exc:
            app.logger.warning("Rejected G2G payload: %s", exc)
            return jsonify(error=str(exc)), exc.status_code
        except Exception:
            db.session.rollback()
            app.logger.exception("Unexpected G2G webhook failure")
            return jsonify(error="internal error"), 500
        return jsonify(outcome.response), outcome.status_code

    return app


app = create_app()


if __name__ == "__main__":
    # External binding is required for the Render web service.
    app.run(
        host="0.0.0.0",  # nosec B104
        port=int(os.getenv("PORT", "5000")),
        debug=False,
    )
