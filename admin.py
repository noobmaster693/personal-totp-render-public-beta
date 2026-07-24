from __future__ import annotations

import functools
import hmac
import json
import re
import secrets
import time
from datetime import datetime, timedelta, timezone

from cryptography.fernet import InvalidToken
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
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash

from extensions import db
from models import (
    AccessAttempt,
    AdminAudit,
    BuyerSession,
    CancellationTombstone,
    DeliveryAttempt,
    Order,
    VisitorEvent,
    WebhookEvent,
)
from security import decrypt_text, generate_csrf_token
from services import (
    cleanup_operational_data,
    create_manual_order,
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


def _order_action_redirect(order_id: int):
    if request.form.get("return_to") == "order":
        return redirect(url_for("admin.order_detail", order_id=order_id))
    return redirect(url_for("admin.dashboard"))


@admin.app_context_processor
def inject_admin_helpers():
    return {"csrf_token": csrf_token}


@admin.route("/login", methods=["GET", "POST"])
def login():
    admin_totp_required = bool(current_app.config["ADMIN_TOTP_REQUIRED"])
    if request.method == "POST":
        _check_csrf()
        if _login_rate_limited():
            flash("Too many failed login attempts. Try again later.", "error")
            return (
                render_template(
                    "admin/login.html",
                    admin_totp_required=admin_totp_required,
                ),
                429,
            )

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
        if valid and admin_totp_required:
            if not admin_totp_secret:
                current_app.logger.error(
                    "ADMIN_TOTP_REQUIRED is true but ADMIN_TOTP_SECRET is missing"
                )
                valid = False
            else:
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
            return (
                render_template(
                    "admin/login.html",
                    admin_totp_required=admin_totp_required,
                ),
                403,
            )

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

    return render_template(
        "admin/login.html",
        admin_totp_required=admin_totp_required,
    )


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
        "unique_visitors": db.session.scalar(
            select(func.count(func.distinct(VisitorEvent.ip_address))).where(
                VisitorEvent.visited_at
                >= datetime.now(timezone.utc) - timedelta(days=30)
            )
        )
        or 0,
    }
    retention_days = int(current_app.config["VISITOR_LOG_RETENTION_DAYS"])
    return render_template(
        "admin/dashboard.html",
        orders=orders,
        events=events,
        attempts=attempts,
        buyer_sessions=buyer_sessions,
        tombstones=tombstones,
        counts=counts,
        retention_days=retention_days,
    )


@admin.route("/orders/new", methods=["GET", "POST"])
@admin_required
def create_manual_key():
    if request.method == "GET":
        return render_template("admin/manual_order.html")

    _check_csrf()
    order_reference = request.form.get("order_reference", "").strip()
    buyer_username = request.form.get("buyer_username", "").strip()
    product_name = request.form.get("product_name", "").strip()
    duration_unit = request.form.get("duration_unit", "days")
    try:
        duration_value = int(request.form.get("duration_value", "0"))
    except ValueError:
        duration_value = 0

    errors = []
    if order_reference and not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._:-]{1,159}", order_reference
    ):
        errors.append(
            "Order reference must use 2–160 letters, numbers, dots, underscores, "
            "colons, or hyphens."
        )
    if len(buyer_username) > 160:
        errors.append("Buyer username must be 160 characters or fewer.")
    if not product_name or len(product_name) > 240:
        errors.append("Product name is required and must be 240 characters or fewer.")
    multiplier = {"hours": 3600, "days": 86400}.get(duration_unit)
    if multiplier is None or duration_value < 1:
        errors.append("Choose a positive duration in hours or days.")
    duration_seconds = duration_value * (multiplier or 0)
    if duration_seconds > 10 * 365 * 86400:
        errors.append("Manual access cannot exceed 10 years.")

    if not order_reference:
        order_reference = (
            f"MANUAL-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-"
            f"{secrets.token_hex(3).upper()}"
        )
    if db.session.scalar(select(Order.id).where(Order.g2g_order_id == order_reference)):
        errors.append("That order reference already exists.")

    if errors:
        for error in errors:
            flash(error, "error")
        return (
            render_template(
                "admin/manual_order.html",
                form={
                    "order_reference": request.form.get("order_reference", ""),
                    "buyer_username": buyer_username,
                    "product_name": product_name,
                    "duration_value": request.form.get("duration_value", ""),
                    "duration_unit": duration_unit,
                },
            ),
            400,
        )

    try:
        order, raw_key = create_manual_order(
            order_id=order_reference,
            product_name=product_name,
            duration_seconds=duration_seconds,
            buyer_username=buyer_username or None,
            return_existing=False,
        )
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "error")
        return render_template("admin/manual_order.html"), 409
    except IntegrityError:
        db.session.rollback()
        flash("That order reference was created by another request.", "error")
        return render_template("admin/manual_order.html"), 409

    audit(
        "manual_order_created",
        target_type="order",
        target_id=str(order.id),
        details={
            "order_reference": order.g2g_order_id,
            "duration_seconds": duration_seconds,
        },
    )
    db.session.commit()
    return render_template(
        "admin/manual_key_created.html",
        order=order,
        raw_key=raw_key,
    )


@admin.get("/orders/<int:order_id>")
@admin_required
def order_detail(order_id: int):
    order = db.session.get(Order, order_id)
    if order is None:
        abort(404)

    now = datetime.now(timezone.utc)
    buyer_sessions = db.session.scalars(
        select(BuyerSession)
        .where(BuyerSession.order_id == order.id)
        .order_by(BuyerSession.last_seen_at.desc())
    ).all()
    access_attempts = db.session.scalars(
        select(AccessAttempt)
        .where(AccessAttempt.order_id == order.id)
        .order_by(AccessAttempt.created_at.desc())
        .limit(200)
    ).all()
    delivery_attempts = db.session.scalars(
        select(DeliveryAttempt)
        .where(DeliveryAttempt.order_id == order.id)
        .order_by(DeliveryAttempt.id.desc())
    ).all()
    webhook_events = db.session.scalars(
        select(WebhookEvent)
        .where(WebhookEvent.g2g_order_id == order.g2g_order_id)
        .order_by(WebhookEvent.received_at.desc())
    ).all()
    ip_summary = (
        db.session.execute(
            select(
                BuyerSession.ip_address.label("ip_address"),
                func.count(BuyerSession.id).label("session_count"),
                func.min(BuyerSession.created_at).label("first_seen"),
                func.max(BuyerSession.last_seen_at).label("last_seen"),
                func.sum(
                    case(
                        (
                            BuyerSession.revoked_at.is_(None)
                            & (BuyerSession.expires_at > now),
                            1,
                        ),
                        else_=0,
                    )
                ).label("active_sessions"),
            )
            .where(BuyerSession.order_id == order.id)
            .group_by(BuyerSession.ip_address)
            .order_by(func.max(BuyerSession.last_seen_at).desc())
        )
        .mappings()
        .all()
    )

    return render_template(
        "admin/order_detail.html",
        order=order,
        now=now,
        buyer_sessions=buyer_sessions,
        access_attempts=access_attempts,
        delivery_attempts=delivery_attempts,
        webhook_events=webhook_events,
        ip_summary=ip_summary,
    )


@admin.post("/orders/<int:order_id>/key")
@admin_required
def reveal_order_key(order_id: int):
    _check_csrf()
    order = db.session.get(Order, order_id)
    if order is None:
        abort(404)

    try:
        raw_key = decrypt_text(order.access_key_ciphertext)
    except InvalidToken:
        audit(
            "access_key_reveal_failed",
            target_type="order",
            target_id=str(order.id),
            details={"order_reference": order.g2g_order_id},
        )
        db.session.commit()
        flash("The stored access key could not be decrypted.", "error")
        return redirect(url_for("admin.order_detail", order_id=order.id))

    audit(
        "access_key_revealed",
        target_type="order",
        target_id=str(order.id),
        details={"order_reference": order.g2g_order_id},
    )
    db.session.commit()
    return render_template(
        "admin/reveal_key.html",
        order=order,
        raw_key=raw_key,
    )


@admin.get("/visitors")
@admin_required
def visitors():
    retention_days = int(current_app.config["VISITOR_LOG_RETENTION_DAYS"])
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    visitor_summary = (
        db.session.execute(
            select(
                VisitorEvent.ip_address.label("ip_address"),
                func.count(VisitorEvent.id).label("visit_count"),
                func.min(VisitorEvent.visited_at).label("first_seen"),
                func.max(VisitorEvent.visited_at).label("last_seen"),
            )
            .where(VisitorEvent.visited_at >= cutoff)
            .group_by(VisitorEvent.ip_address)
            .order_by(func.max(VisitorEvent.visited_at).desc())
            .limit(500)
        )
        .mappings()
        .all()
    )
    recent_visits = db.session.scalars(
        select(VisitorEvent)
        .where(VisitorEvent.visited_at >= cutoff)
        .order_by(VisitorEvent.visited_at.desc())
        .limit(200)
    ).all()
    return render_template(
        "admin/visitors.html",
        visitor_summary=visitor_summary,
        recent_visits=recent_visits,
        retention_days=retention_days,
        visitor_log_enabled=bool(current_app.config["VISITOR_LOG_ENABLED"]),
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
    return _order_action_redirect(order_id)


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
    return _order_action_redirect(order_id)


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
    return _order_action_redirect(order_id)


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
    return _order_action_redirect(order_id)


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
    if request.form.get("return_to") == "order":
        try:
            order_id = int(request.form.get("order_id", ""))
        except ValueError:
            order_id = 0
        if order_id and db.session.get(Order, order_id) is not None:
            return redirect(url_for("admin.order_detail", order_id=order_id))
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
        f"{result['buyer_sessions']} expired sessions, plus "
        f"{result['visitor_events']} visitor events.",
        "success",
    )
    return redirect(url_for("admin.dashboard"))
