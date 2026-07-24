# Temporary G2G TOTP Access Portal

A Flask/PostgreSQL service for selling time-limited access to one shared
software account. Each G2G order receives the shared login, a buyer-specific
portal key, and access to the current TOTP code until the order expires or is
revoked.

The permanent TOTP secret stays encrypted or in the service environment. It is
never returned to buyers.

## Included

- G2G `order.api_delivery`, cancellation, refund, and delivery-status webhooks;
- current documented webhook signature and payload parsing;
- durable webhook event ledger and conflict detection;
- PostgreSQL per-order advisory locking;
- cancellation/refund tombstones for out-of-order events;
- idempotent access-key creation;
- G2G delivery lookup, retries, and HTTP 409 status reconciliation;
- server-side, individually revocable buyer sessions;
- automatic order and session expiration;
- `/admin` operations and encrypted account-settings portal;
- administrator password plus separate optional/production-required TOTP;
- admin audit records;
- Alembic fresh and legacy-schema migrations;
- separate `/live` and `/ready` probes;
- SQLite unit tests and PostgreSQL concurrency integration tests.

Use this only for software and an account that you own or are authorized to
distribute, and only where G2G and the software terms permit shared access.

## Purchase flow

```text
G2G order.api_delivery
  -> verify signature and timestamp
  -> ledger event and lock order
  -> reject conflicts or cancellation tombstones
  -> create one order and one buyer key
  -> resolve G2G delivery_id
  -> deliver login, portal URL, key, and expiration
  -> buyer unlocks a revocable server-side session
  -> portal returns current TOTP until expiry/revocation
```

## G2G payload compatibility

The webhook verifier requires the documented `g2g-signature` and
`g2g-timestamp` headers. The configured API key and seller user ID are used to
reconstruct the signature. If G2G also supplies identity headers, they are
validated but are not required.

For `order.api_delivery`, the parser accepts the documented `purchased_qty`
field as well as legacy `purchased_quantity` and `quantity` variants. It reads
`delivery_method_list` but does **not** incorrectly treat
`delivery_method_id` as a delivery operation ID. If the event contains no
actual `delivery_id`, the service calls G2G Get Deliveries and selects one
unambiguous delivery record before calling Deliver Code.

`additional_info_list` and `delivery_method_list` may be empty and are not
required merely to acknowledge a valid order. Unknown signed event types are
stored and acknowledged but never used to fulfill an order. In particular,
`order.created` is not treated as proof that an order is paid.

Reference:

- [G2G order.api_delivery](https://docs.g2g.com/order-api-delivery-18583502e0)
- [G2G order delivery flow](https://docs.g2g.com/order-delivery-flow-1237157m0)
- [G2G webhook signature](https://docs.g2g.com/message-signature-1237168m0)
- [G2G Get Deliveries](https://docs.g2g.com/get-deliveries-18583490e0)
- [G2G Deliver Code](https://docs.g2g.com/deliver-code-18583491e0)
- [G2G Get Delivery Status](https://docs.g2g.com/get-delivery-status-18583492e0)

## Production requirements

When `APP_ENV=production`, startup readiness requires:

- a `postgresql://` or `postgres://` `DATABASE_URL`;
- HTTPS `PUBLIC_BASE_URL`;
- HTTPS `G2G_WEBHOOK_CANONICAL_URL` when G2G is enabled;
- secure session cookies;
- administrator username and password hash;
- a separate administrator TOTP secret.

SQLite and HTTP remain available for local development and tests.

Generate independent secrets:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
python -c "import secrets; print(secrets.token_hex(32))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
python -c "import base64, secrets; print(base64.b32encode(secrets.token_bytes(20)).decode())"
```

Use them for:

```text
SECRET_KEY
ACCESS_KEY_PEPPER
DATA_ENCRYPTION_KEY
ADMIN_TOTP_SECRET
```

Install dependencies and generate the admin password hash without putting the
password on the command line:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py hash-admin-password
```

Store the resulting hash in `ADMIN_PASSWORD_HASH`.

Do not change `ACCESS_KEY_PEPPER` while orders are active; existing buyer keys
depend on it. Do not lose `DATA_ENCRYPTION_KEY`; it decrypts stored delivery
keys, webhook fixtures, and account settings.

## Required environment

Start from `.env.example`. Important production values are:

```text
APP_ENV=production
DATABASE_URL=<persistent PostgreSQL internal URL>
SECRET_KEY=<random value>
ACCESS_KEY_PEPPER=<different random value>
DATA_ENCRYPTION_KEY=<Fernet key>

PUBLIC_BASE_URL=https://your-service.onrender.com

ADMIN_USERNAME=<private administrator username>
ADMIN_PASSWORD_HASH=<Werkzeug password hash>
ADMIN_TOTP_SECRET=<separate Base32 secret>

TOTP_SECRET=<shared account Base32 secret or otpauth URI>
TOTP_LABEL=Main Software Account
TOTP_ISSUER=Your Software
SOFTWARE_PROVIDER=Email
SOFTWARE_LOGIN_EMAIL=<shared software login>
SOFTWARE_LOGIN_PASSWORD=<shared software password>
```

The shared account values can later be replaced through `/admin/settings`.
Database values are encrypted and take precedence over environment fallbacks.
Secret values are never displayed back in the admin interface.

## Product duration mapping

Map exact G2G offer IDs to access durations:

```text
G2G_PRODUCTS_JSON={"REAL_OFFER_ID_30D":{"name":"Software access - 30 days","duration_days":30},"REAL_OFFER_ID_90D":{"name":"Software access - 90 days","duration_days":90}}
```

Each offer defaults to `max_quantity: 1`. Set an explicit larger value only if
the duration semantics for multiple quantities are intentional.

## G2G setup

Configure:

```text
G2G_INTEGRATION_ENABLED=false
G2G_API_BASE=https://open-api.g2g.com
G2G_API_VERSION=v2
G2G_API_KEY=<seller API key>
G2G_API_SECRET=<seller API secret>
G2G_USER_ID=<seller user ID>
G2G_WEBHOOK_SECRET=<webhook secret token>
G2G_WEBHOOK_CANONICAL_URL=https://your-service.onrender.com/webhooks/g2g
```

The canonical URL must match the URL registered with G2G exactly.

Subscribe to:

```text
order.api_delivery
order.cancelled
order.refunded
order.delivery_status
```

Keep integration disabled until a signed fixture or real sandbox event has
passed. Then set `G2G_INTEGRATION_ENABLED=true` and redeploy.

## Database migration

The application no longer calls `db.create_all()` during web startup.

Run:

```bash
alembic upgrade head
```

The first migration supports both an empty database and the previous
`orders`/`access_attempts` schema. Existing order IDs, encrypted keys, and
access-key hashes are preserved.

The Render Blueprint runs migrations before starting Gunicorn and uses
`/ready` as its health check. For a scaled deployment, move the same Alembic
command to Render's pre-deploy command so only one migration runner operates
before new instances start.

## Local development

Use development settings:

```text
APP_ENV=development
DATABASE_URL=sqlite:///local.db
SESSION_COOKIE_SECURE=false
PUBLIC_BASE_URL=http://127.0.0.1:5000
G2G_INTEGRATION_ENABLED=false
```

Then:

```bash
alembic upgrade head
python manage.py create-test-key --order-id LOCAL-001 --name "One hour test" --hours 1
python app.py
```

Open `http://127.0.0.1:5000`. Administrator operations are at
`http://127.0.0.1:5000/admin`.

## Administration and operations

The admin dashboard shows:

- orders and delivery state;
- buyer IDs and current access state;
- buyer session IP, browser, timezone, and language hints;
- webhook event status and conflicts;
- delivery attempts and errors;
- cancellation/refund tombstones.

It supports order revocation, individual/all-session revocation, forced
delivery retry, and G2G delivery-status reconciliation.

Operational commands:

```bash
python manage.py list-orders
python manage.py expire-orders
python manage.py retry-deliveries --limit 50
python manage.py reconcile-delivery --order-id "G2G_ORDER_ID"
python manage.py cleanup --days 90
```

Schedule `python manage.py retry-deliveries --limit 50` every five minutes in a
Render Cron Job using the same environment values as the web service. Webhook
redeliveries also retry failed fulfillment immediately.

## Tests

Run:

```bash
pip install -r requirements-dev.txt
ruff check .
ruff format --check .
bandit -q -r . -x './tests,./migrations'
python -m unittest discover -s tests -v
```

The GitHub Actions workflow starts PostgreSQL and additionally exercises
concurrent duplicate delivery. Locally, PostgreSQL tests run when
`TEST_DATABASE_URL` is set:

```bash
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/totp_test \
python -m unittest tests.test_postgres -v
```

The suite covers current G2G fixtures, documented signature headers,
idempotency, event/order conflicts, cancellation-before-order, delivery retry,
HTTP 409 reconciliation, fresh/legacy migrations, admin controls, session
revocation, and production configuration enforcement.

## Shared-account limitation

Revoking an order or buyer session immediately stops future portal codes. It
cannot force-log-out a session that is already authenticated inside the
software unless that software exposes and uses a supported session-revocation
mechanism.
