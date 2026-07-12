from __future__ import annotations

import argparse

from app import create_app
from extensions import db
from models import Order
from services import create_manual_order, expire_due_orders, revoke_order

app = create_app()


def init_db(_args):
    with app.app_context():
        db.create_all()
        print("Database tables are ready.")


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
        orders = db.session.scalars(
            db.select(Order).order_by(Order.id.desc())
        ).all()
        if not orders:
            print("No orders.")
            return
        for order in orders:
            print(
                f"{order.g2g_order_id} | {order.product_name} | "
                f"{order.status} | delivery={order.delivery_status} | "
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


parser = argparse.ArgumentParser(
    description="Temporary TOTP portal management commands"
)
sub = parser.add_subparsers(required=True)

command = sub.add_parser("init-db")
command.set_defaults(func=init_db)

command = sub.add_parser("create-test-key")
command.add_argument("--order-id", required=True)
command.add_argument("--name", default="Local test access")
command.add_argument("--hours", required=True, type=int)
command.set_defaults(func=create_key)

command = sub.add_parser("list-orders")
command.set_defaults(func=list_orders)

command = sub.add_parser("revoke-order")
command.add_argument("--order-id", required=True)
command.set_defaults(func=revoke)

command = sub.add_parser("expire-orders")
command.set_defaults(func=expire)

args = parser.parse_args()
args.func(args)
