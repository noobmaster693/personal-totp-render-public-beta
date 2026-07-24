from __future__ import annotations

import argparse
import getpass

from alembic import command
from alembic.config import Config
from werkzeug.security import generate_password_hash

from app import create_app
from extensions import db
from models import Order
from services import (
    cleanup_operational_data,
    create_manual_order,
    expire_due_orders,
    revoke_order,
)
from webhook_service import reconcile_delivery, retry_due_deliveries

app = create_app()


def init_db(_args):
    command.upgrade(Config("alembic.ini"), "head")
    print("Database migrations are at head.")


def create_key(args):
    with app.app_context():
        order, raw_key = create_manual_order(
            order_id=args.order_id,
            product_name=args.name,
            duration_seconds=args.hours * 3600,
        )
        print(f"Order ID: {order.g2g_order_id}")
        print(f"Access key: {raw_key}")
        print(f"Expires: {order.expires_at.isoformat()}")
        print(f"Portal: {app.config['PUBLIC_BASE_URL']}")


def list_orders(_args):
    with app.app_context():
        orders = db.session.scalars(db.select(Order).order_by(Order.id.desc())).all()
        if not orders:
            print("No orders.")
            return
        for order in orders:
            print(
                f"{order.g2g_order_id} | {order.product_name} | "
                f"{order.status} | delivery={order.delivery_status} | "
                f"attempts={order.delivery_attempts} | "
                f"expires={order.expires_at.isoformat()}"
            )


def revoke(args):
    with app.app_context():
        found = revoke_order(args.order_id, reason="manual revocation")
        print("Revoked." if found else "Order not found.")


def expire(_args):
    with app.app_context():
        count = expire_due_orders()
        print(f"Expired {count} order(s).")


def retry_deliveries(args):
    with app.app_context():
        result = retry_due_deliveries(limit=args.limit)
        print(
            f"Attempted {result['attempted']}; "
            f"delivered {result['delivered']}; failed {result['failed']}."
        )


def reconcile(args):
    with app.app_context():
        order = db.session.scalar(
            db.select(Order).where(Order.g2g_order_id == args.order_id)
        )
        if order is None:
            raise SystemExit("Order not found.")
        order_id = order.id
        db.session.rollback()
        outcome = reconcile_delivery(order_id)
        print(outcome.response)
        if outcome.status_code != 200:
            raise SystemExit(1)


def cleanup(args):
    with app.app_context():
        result = cleanup_operational_data(older_than_days=args.days)
        print(result)


def hash_admin_password(args):
    password = args.password or getpass.getpass("Administrator password: ")
    if len(password) < 12:
        raise SystemExit("Use an administrator password of at least 12 characters.")
    print(generate_password_hash(password))


parser = argparse.ArgumentParser(
    description="Temporary TOTP portal management commands"
)
sub = parser.add_subparsers(required=True)

command_parser = sub.add_parser("init-db")
command_parser.set_defaults(func=init_db)

command_parser = sub.add_parser("create-test-key")
command_parser.add_argument("--order-id", required=True)
command_parser.add_argument("--name", default="Local test access")
command_parser.add_argument("--hours", required=True, type=int)
command_parser.set_defaults(func=create_key)

command_parser = sub.add_parser("list-orders")
command_parser.set_defaults(func=list_orders)

command_parser = sub.add_parser("revoke-order")
command_parser.add_argument("--order-id", required=True)
command_parser.set_defaults(func=revoke)

command_parser = sub.add_parser("expire-orders")
command_parser.set_defaults(func=expire)

command_parser = sub.add_parser("retry-deliveries")
command_parser.add_argument("--limit", default=50, type=int)
command_parser.set_defaults(func=retry_deliveries)

command_parser = sub.add_parser("reconcile-delivery")
command_parser.add_argument("--order-id", required=True)
command_parser.set_defaults(func=reconcile)

command_parser = sub.add_parser("cleanup")
command_parser.add_argument("--days", default=90, type=int)
command_parser.set_defaults(func=cleanup)

command_parser = sub.add_parser("hash-admin-password")
command_parser.add_argument("password", nargs="?")
command_parser.set_defaults(func=hash_admin_password)

args = parser.parse_args()
args.func(args)
