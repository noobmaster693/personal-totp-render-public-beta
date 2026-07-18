# G2G TOTP Access Portal

A Flask portal that issues buyer-specific, expiring access keys and reveals the current TOTP code only while an authorized order is active. It supports G2G webhooks and delivery, PostgreSQL persistence, signed browser sessions, and deployment on Render.

## Responsible use

Use this project only with an account and software subscription that you own or are explicitly authorized to distribute, and only when both the software provider and G2G permit the access model. It must not be used to bypass 2FA, evade access controls, resell unauthorized accounts, or expose another person's credentials.

The permanent TOTP secret remains on the server. Buyers receive a random access key and can request only the current short-lived code until their order expires or is revoked.

## Features

- Buyer-specific access keys stored as hashes
- Automatic access expiration and manual revocation
- Encrypted storage for credentials needed during delivery retries
- Signed, HTTP-only browser sessions
- Rate limiting on access-key attempts
- Persistent order records in PostgreSQL
- G2G `order.api_delivery` webhook fulfillment
- Automatic revocation for cancellation and refund events
- Idempotent processing of repeated order webhooks
- Render Blueprint configuration
- RFC 6238 and portal behavior tests

## How it works

```text
G2G purchase
  -> signed webhook received
  -> seller and offer validated
  -> random buyer access key created
  -> order and expiration stored
  -> portal details and key delivered through G2G
  -> buyer unlocks the portal
  -> current TOTP code is available until expiration or revocation
```

The `/api/code` endpoint returns `401` until a valid buyer key has unlocked a signed session. Expiration is checked on every portal request, so a scheduled job is not required to stop access.

## Requirements

- Python 3.10 or newer
- SQLite for local development
- PostgreSQL for a persistent production deployment
- A TOTP Base32 secret or complete `otpauth://totp/...` URI
- Optional: approved G2G OpenAPI/API Integration access

## Local quick start

Clone the project and create a virtual environment:

```bash
git clone https://github.com/noobmaster693/personal-totp-render-public-beta.git
cd personal-totp-render-public-beta
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

On Windows Command Prompt, activate with `.venv\Scripts\activate` and copy the template with `copy .env.example .env`.

Generate three independent secrets:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
python -c "import secrets; print(secrets.token_hex(32))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Put the results in `.env` as `SECRET_KEY`, `ACCESS_KEY_PEPPER`, and `DATA_ENCRYPTION_KEY`. For local testing, keep:

```dotenv
DATABASE_URL=sqlite:///local.db
SESSION_COOKIE_SECURE=false
PUBLIC_BASE_URL=http://127.0.0.1:5000
G2G_INTEGRATION_ENABLED=false
```

Set `TOTP_SECRET` to a test credential that you control. Do not use a production secret until the local workflow is verified.

Create the database and a one-hour test key:

```bash
python manage.py init-db
python manage.py create-test-key --order-id LOCAL-001 --name "One hour test" --hours 1
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) and enter the generated access key.

## Management commands

| Command | Purpose |
| --- | --- |
| `python manage.py init-db` | Create missing database tables. |
| `python manage.py create-test-key --order-id ID --name NAME --hours N` | Create a manual temporary-access order and print its key. |
| `python manage.py list-orders` | List stored orders and delivery state. |
| `python manage.py revoke-order --order-id ID` | Immediately revoke an order. |
| `python manage.py expire-orders` | Mark due orders as expired for housekeeping. |

Manual key creation prints a raw access key once. Handle terminal logs as sensitive data.

## Run the tests

```bash
python -m unittest discover -s tests -v
```

The test suite verifies RFC 6238 SHA-1 vectors, locked and unlocked portal behavior, expiration, health reporting, and disabled-by-default G2G webhooks. GitHub Actions runs the same suite on pushes and pull requests.

## Deploy to Render

The included `render.yaml` defines the Flask web service and Gunicorn start command. A production deployment also needs a persistent Render PostgreSQL database.

1. Create a Render PostgreSQL database.
2. Deploy this repository as a Blueprint or web service.
3. Copy the database's internal connection URL into `DATABASE_URL`.
4. Add the required environment variables listed below.
5. Keep `G2G_INTEGRATION_ENABLED=false` for the first deployment.
6. Open `/health` and verify that the application and database are ready.
7. Create and test a short manual key before configuring G2G.

Use these production settings:

```dotenv
DATABASE_URL=postgresql://...internal-render-url...
SESSION_COOKIE_SECURE=true
PUBLIC_BASE_URL=https://your-service.onrender.com
```

Do not use SQLite on Render: the web service filesystem is not persistent.

## Required production secrets

Store all real values in Render environment variables, never in GitHub:

```text
SECRET_KEY
ACCESS_KEY_PEPPER
DATA_ENCRYPTION_KEY
TOTP_SECRET
SOFTWARE_LOGIN_EMAIL
SOFTWARE_LOGIN_PASSWORD
PUBLIC_BASE_URL
DATABASE_URL
```

`SOFTWARE_LOGIN_PASSWORD` is the password for the distributed software account. It is not necessarily the email mailbox password.

Do not change `ACCESS_KEY_PEPPER` while active orders exist; existing access keys will stop validating. Do not lose `DATA_ENCRYPTION_KEY`; it is required to retry delivery for an existing order.

## Configure G2G integration

Request OpenAPI/API Integration access from the same G2G seller account that owns the offers. After approval, configure:

```dotenv
G2G_API_KEY=
G2G_API_SECRET=
G2G_USER_ID=
G2G_WEBHOOK_SECRET=
```

### Map offers to access durations

Create one G2G offer per duration and map the exact offer IDs in `G2G_PRODUCTS_JSON`:

```json
{
  "REAL_OFFER_ID_30D": {
    "name": "Software access - 30 days",
    "duration_days": 30
  },
  "REAL_OFFER_ID_90D": {
    "name": "Software access - 90 days",
    "duration_days": 90
  }
}
```

Render environment-variable values must be entered on one line:

```text
G2G_PRODUCTS_JSON={"REAL_OFFER_ID_30D":{"name":"Software access - 30 days","duration_days":30},"REAL_OFFER_ID_90D":{"name":"Software access - 90 days","duration_days":90}}
```

Each offer defaults to a maximum order quantity of one so that one purchase event cannot be interpreted as multiple subscriptions.

### Configure the webhook

Set the webhook URL to:

```text
https://your-service.onrender.com/webhooks/g2g
```

Subscribe to:

```text
order.api_delivery
order.cancelled
order.refunded
```

Set the exact canonical URL used for signature verification:

```dotenv
G2G_WEBHOOK_CANONICAL_URL=https://your-service.onrender.com/webhooks/g2g
```

The scheme, hostname, path, and trailing slash must exactly match the URL registered with G2G.

### Test and enable

Before enabling fulfillment:

- verify a manual one-hour key;
- test webhook signature rejection and acceptance;
- confirm the seller ID and offer ID mapping;
- test delivery using a short-duration test offer;
- test refund and cancellation revocation.

Then set:

```dotenv
G2G_INTEGRATION_ENABLED=true
```

For `order.api_delivery`, the application verifies the signature and seller, validates the offer mapping, creates one key, records its expiration, and calls the G2G Deliver Code endpoint. Repeated webhooks for the same order reuse the existing record instead of creating duplicate access.

If G2G's current API console uses a different delivery path, set `G2G_DELIVERY_PATH_TEMPLATE` to the documented path without changing application code.

## Main endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Report application and database health. |
| `GET` | `/` | Show the buyer unlock portal. |
| `POST` | `/unlock` | Validate an access key and create a signed session. |
| `POST` | `/logout` | Clear the buyer session. |
| `GET` | `/api/code` | Return the current TOTP code for an authorized session. |
| `POST` | `/webhooks/g2g` | Process supported signed G2G order events. |

## Configuration reference

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLite URL locally or PostgreSQL URL in production. |
| `SECRET_KEY` | Signs Flask browser sessions. |
| `ACCESS_KEY_PEPPER` | Protects stored access-key hashes. |
| `DATA_ENCRYPTION_KEY` | Encrypts credentials retained for delivery retries. |
| `TOTP_SECRET` | Base32 secret or `otpauth://` URI used to generate codes. |
| `TOTP_LABEL` / `TOTP_ISSUER` | Human-readable account metadata. |
| `SOFTWARE_PROVIDER` | Name delivered to the buyer. |
| `SOFTWARE_LOGIN_EMAIL` / `SOFTWARE_LOGIN_PASSWORD` | Authorized software account credentials. |
| `PUBLIC_BASE_URL` | Public portal origin included in delivery. |
| `G2G_INTEGRATION_ENABLED` | Enables or disables webhook fulfillment. |
| `G2G_API_KEY` / `G2G_API_SECRET` / `G2G_USER_ID` | G2G API identity. |
| `G2G_WEBHOOK_SECRET` | Verifies webhook signatures. |
| `G2G_WEBHOOK_CANONICAL_URL` | Exact URL used during signature verification. |
| `G2G_PRODUCTS_JSON` | Maps offer IDs to names and durations. |
| `RATE_LIMIT_ATTEMPTS` / `RATE_LIMIT_WINDOW_SECONDS` | Controls unlock-attempt throttling. |

See `.env.example` for defaults and the complete set of optional G2G settings.

## Production checklist

- Use PostgreSQL and HTTPS.
- Keep all credentials in Render environment variables.
- Keep `SESSION_COOKIE_SECURE=true`.
- Use independent, randomly generated application secrets.
- Verify that the software license permits the intended users and duration.
- Limit offer quantity and test short access periods first.
- Monitor failed webhook delivery and revocation events.
- Rotate exposed secrets immediately and revoke affected orders.
- Do not publish screenshots, logs, database exports, or `.env` files containing buyer or account data.

## Project status

This project is an integration template, not a turnkey entitlement or identity platform. Review current G2G documentation and your software provider's terms before production use, and obtain a security review for any deployment handling real credentials or payments.
