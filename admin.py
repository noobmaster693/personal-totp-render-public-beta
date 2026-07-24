from __future__ import annotations

import functools
import hmac
import json
import time
from datetime import datetime, timedelta, timezone

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import func, select
from werkzeug.security import check_password_hash

from extensions import db
from models import (
    AdminAudit,
    BuyerSession,
    CancellationTombstone,
    DeliveryAttempt,
    Order,
    WebhookEvent,
)
from security import generate_csrf_token
from services import (
    cleanup_operational_data,
    revoke_buyer_sessions,
    revoke_order,
    revoke_session,
)
from settings_service import get_account_settings, save_account_settings
from totp import parse_totp_config, verify_totp
from webhook_service import (
    attempt_delivery,
    reconcile_delivery,
    retry_due_deliveries,
)

admin = Blueprint("admin", __name__, url_prefix="/admin")


def _client_ip() -> str:
    return request.remote_addr or "unknown"


def csrf_token() -> str:
    token = session.get("_csrf_token")
    if not isinstance(token, str):
        token = generate_csrf_token()
        session["_csrf_token"] = token
    return token


def _check_csrf() -> None:
    expected = session.get("_csrf_token", "")
    supplied = request.form.get("_csrf_token", "")
    if (
        not isinstance(expected, str)
        or not expected
        or not hmac.compare_digest(expected, supplied)
    ):
        abort(400, "Invalid CSRF token")


def _admin_logged_in() -> bool:
    authenticated_at = session.get("admin_authenticated_at")
    if not isinstance(authenticated_at, (int, float)):
        return False
    lifetime = int(current_app.config["ADMIN_SESSION_HOURS"]) * 3600
    return time.time() - float(authenticated_at) <= lifetime


def admin_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not _admin_logged_in():
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def audit(
    action: str,
    *,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict | None = None,
    actor: str | None = None,
) -> None:
    db.session.add(
        AdminAudit(
            actor=(actor or str(session.get("admin_user") or "anonymous"))[:160],
            action=action[:120],
            target_type=target_type[:80] if target_type else None,
            target_id=target_id[:180] if target_id else None,
            ip_address=_client_ip()[:80],
            user_agent=request.headers.get("User-Agent", "")[:1000],
            details_json=(
                json.dumps(details, sort_keys=True)[:4000] if details else None
            ),
        )
    )


def _login_rate_limited() -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(
        seconds=int(current_app.config["ADMIN_LOGIN_WINDOW_SECONDS"])
    )
    count = db.session.scalar(
        select(func.count(AdminAudit.id)).where(
            AdminAudit.action == "login_failed",
            AdminAudit.ip_address == _client_ip(),
            AdminAudit.created_at >= cutoff,
        )
    )
    return int(count or 0) >= int(current_app.config["ADMIN_LOGIN_ATTEMPTS"])


@admin.app_context_processor
def inject_admin_helpers():
    return {"csrf_token": csrf_token}


@admin.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        _check_csrf()
        if _login_rate_limited():
            flash("Too many failed login attempts. Try again later.", "error")
            return render_template("admin/login.html"), 429

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        totp_code = request.form.get("totp_code", "")
        expected_user = current_app.config.get("ADMIN_USERNAME", "")
        password_hash = current_app.config.get("ADMIN_PASSWORD_HASH", "")
        valid = bool(
            expected_user
            and password_hash
            and hmac.compare_digest(username, expected_user)
            and check_password_hash(password_hash, password)
        )

        admin_totp_secret = current_app.config.get("ADMIN_TOTP_SECRET", "")
        if valid and admin_totp_secret:
            try:
                config = parse_totp_config(
                    admin_totp_secret, "Portal admin", "TOTP Portal"
                )
                valid = verify_totp(config, totp_code, window=1)
            except ValueError:
                current_app.logger.error("ADMIN_TOTP_SECRET is invalid")
                valid = False

        if not valid:
            audit("login_failed", actor=username or "unknown")
            db.session.commit()
            flash("Invalid administrator credentials.", "error")
            return render_template("admin/login.html"), 403

        session["admin_user"] = username
        session["admin_authenticated_at"] = int(time.time())
        session.permanent = True
        session["_csrf_token"] = generate_csrf_token()
        audit("login_success")
        db.session.commit()
        next_url = request.args.get("next", "")
        if not next_url.startswith("/admin"):
            next_url = url_for("admin.dashboard")
        return redirect(next_url)

    return render_template("admin/login.html")


@admin.post("/logout")
@admin_required
def logout():
    _check_csrf()
    audit("logout")
    db.session.commit()
    for key in ("admin_user", "admin_authenticated_at", "_csrf_token"):
        session.pop(key, None)
    return redirect(url_for("admin.login"))


@admin.get("/")
@admin_required
def dashboard():
    orders = db.session.scalars(
        select(Order).order_by(Order.id.desc()).limit(100)
    ).all()
    events = db.session.scalars(
        select(WebhookEvent).order_by(WebhookEvent.id.desc()).limit(100)
    ).all()
    attempts = db.session.scalars(
        select(DeliveryAttempt).order_by(DeliveryAttempt.id.desc()).limit(100)
    ).all()
    buyer_sessions = db.session.scalars(
        select(BuyerSession).order_by(BuyerSession.id.desc()).limit(100)
    ).all()
    tombstones = db.session.scalars(
        select(CancellationTombstone)
        .order_by(CancellationTombstone.id.desc())
        .limit(100)
    ).all()
    counts = {
        "active_orders": db.session.scalar(
            select(func.count(Order.id)).where(Order.status == "active")
        )
        or 0,
        "failed_deliveries": db.session.scalar(
            select(func.count(Order.id)).where(Order.delivery_status == "failed")
        )
        or 0,
        "active_sessions": db.session.scalar(
            select(func.count(BuyerSession.id)).where(
                BuyerSession.revoked_at.is_(None),
                BuyerSession.expires_at > datetime.now(timezone.utc),
            )
        )
        or 0,
        "webhook_conflicts": db.session.scalar(
            select(func.count(WebhookEvent.id)).where(WebhookEvent.status == "conflict")
        )
        or 0,
    }
    return render_template(
        "admin/dashboard.html",
        orders=orders,
        events=events,
        attempts=attempts,
        buyer_sessions=buyer_sessions,
        tombstones=tombstones,
        counts=counts,
    )


@admin.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    if request.method == "POST":
        _check_csrf()
        try:
            save_account_settings(
                provider=request.form.get("provider", ""),
                login_email=request.form.get("login_email", ""),
                login_password=request.form.get("login_password") or None,
                totp_secret=request.form.get("totp_secret") or None,
                totp_label=request.form.get("totp_label", ""),
                totp_issuer=request.form.get("totp_issuer", ""),
            )
        except ValueError as exc:
            flash(str(exc), "error")
        else:
            audit("settings_updated", target_type="portal_settings", target_id="1")
            db.session.commit()
            flash("Encrypted account settings updated.", "success")
            return redirect(url_for("admin.settings"))

    try:
        account = get_account_settings()
    except ValueError:
        account = None
    return render_template("admin/settings.html", account=account)


@admin.post("/orders/<int:order_id>/revoke")
@admin_required
def revoke_order_route(order_id: int):
    _check_csrf()
    order = db.session.get(Order, order_id)
    if order is None:
        abort(404)
    g2g_order_id = order.g2g_order_id
    db.session.rollback()
    revoke_order(g2g_order_id, reason="admin revocation")
    audit("order_revoked", target_type="order", target_id=str(order_id))
    db.session.commit()
    flash(f"Order {g2g_order_id} revoked.", "success")
    return redirect(url_for("admin.dashboard"))


@admin.post("/orders/<int:order_id>/retry")
@admin_required
def retry_order_route(order_id: int):
    _check_csrf()
    outcome = attempt_delivery(order_id, force=True)
    audit(
        "delivery_retried",
        target_type="order",
        target_id=str(order_id),
        details={"status_code": outcome.status_code},
    )
    db.session.commit()
    flash(
        outcome.response.get("error")
        or f"Delivery status: {outcome.response.get('delivery_status')}",
        "success" if outcome.status_code == 200 else "error",
    )
    return redirect(url_for("admin.dashboard"))


@admin.post("/orders/<int:order_id>/reconcile")
@admin_required
def reconcile_order_route(order_id: int):
    _check_csrf()
    outcome = reconcile_delivery(order_id)
    audit(
        "delivery_reconciled",
        target_type="order",
        target_id=str(order_id),
        details={"status_code": outcome.status_code, **outcome.response},
    )
    db.session.commit()
    flash(
        outcome.response.get("error")
        or f"G2G status: {outcome.response.get('delivery_status')}",
        "success" if outcome.status_code == 200 else "error",
    )
    return redirect(url_for("admin.dashboard"))


@admin.post("/orders/<int:order_id>/sessions/revoke")
@admin_required
def revoke_order_sessions_route(order_id: int):
    _check_csrf()
    count = revoke_buyer_sessions(order_id, reason="admin session revocation")
    audit(
        "order_sessions_revoked",
        target_type="order",
        target_id=str(order_id),
        details={"count": count},
    )
    db.session.commit()
    flash(f"Revoked {count} active session(s).", "success")
    return redirect(url_for("admin.dashboard"))


@admin.post("/sessions/<int:session_id>/revoke")
@admin_required
def revoke_session_route(session_id: int):
    _check_csrf()
    found = revoke_session(session_id, reason="admin session revocation")
    audit(
        "session_revoked",
        target_type="buyer_session",
        target_id=str(session_id),
        details={"found": found},
    )
    db.session.commit()
    flash("Session revoked." if found else "Session not found.", "success")
    return redirect(url_for("admin.dashboard"))


@admin.post("/operations/retry-due")
@admin_required
def retry_due_route():
    _check_csrf()
    result = retry_due_deliveries()
    audit("retry_due_deliveries", details=result)
    db.session.commit()
    flash(
        f"Attempted {result['attempted']} delivery retries; "
        f"{result['delivered']} succeeded.",
        "success",
    )
    return redirect(url_for("admin.dashboard"))


@admin.post("/operations/cleanup")
@admin_required
def cleanup_route():
    _check_csrf()
    days = max(30, min(3650, int(request.form.get("days", "90"))))
    result = cleanup_operational_data(older_than_days=days)
    audit("operational_cleanup", details={"days": days, **result})
    db.session.commit()
    flash(
        f"Removed {result['access_attempts']} access attempts and "
        f"{result['buyer_sessions']} expired sessions.",
        "success",
    )
    return redirect(url_for("admin.dashboard"))
