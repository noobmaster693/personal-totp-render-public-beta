# Temporary G2G TOTP Access Portal

This repository combines the existing Render-hosted authenticator page with:

- one shared email-based software account;
- buyer-specific temporary access keys;
- automatic expiration;
- a persistent order database;
- G2G `order.api_delivery` webhook processing;
- automatic credential/key delivery through the G2G API;
- cancellation and refund revocation;
- rate limiting and signed browser sessions.

The permanent TOTP setup secret stays in Render. Buyers receive only the current short-lived code after entering the key linked to their purchase.

Use this only for software and an email-based account that you own or are authorized to distribute, and only where the software provider and G2G permit the shared-access model.

## What changed from the public beta

Previously, `/api/code` returned the TOTP code to anyone. It now returns `401` until a valid buyer access key has been entered.

```text
G2G purchase
  -> G2G webhook
  -> generate access key
  -> save order and expiration
  -> deliver email/password/portal/key through G2G
  -> buyer unlocks portal
  -> portal returns current TOTP until expiration
```

## Render environment variables

Keep all real secrets in Render, never in GitHub.

Generate three independent values:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
python -c "import secrets; print(secrets.token_hex(32))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Use them for:

```text
SECRET_KEY
ACCESS_KEY_PEPPER
DATA_ENCRYPTION_KEY
```

Add these Render variables:

```text
DATABASE_URL=<persistent PostgreSQL internal URL>
SECRET_KEY=<first random value>
ACCESS_KEY_PEPPER=<second random value>
DATA_ENCRYPTION_KEY=<Fernet value>

TOTP_SECRET=<existing Base32 or otpauth URI>
TOTP_LABEL=Main Software Account
TOTP_ISSUER=Your Software

SOFTWARE_PROVIDER=Gmail
SOFTWARE_LOGIN_EMAIL=<email used to sign into your software>
SOFTWARE_LOGIN_PASSWORD=<software account password>

PUBLIC_BASE_URL=https://your-render-service.onrender.com
```

`SOFTWARE_LOGIN_PASSWORD` is the password for the software account. It does not need to be the Gmail/Outlook mailbox password unless your own software literally uses that same password.

Do not change `ACCESS_KEY_PEPPER` while active orders exist. Changing it makes all existing buyer keys fail. Do not lose `DATA_ENCRYPTION_KEY`; it is required to retry delivery of an already-created order.

## Database

Create a persistent Render PostgreSQL database and copy its **internal** connection URL into `DATABASE_URL`.

The app creates its tables automatically at startup. SQLite remains available for local testing but should not be used on Render because the web service filesystem is not persistent.

## Test before enabling G2G

Keep:

```text
G2G_INTEGRATION_ENABLED=false
SESSION_COOKIE_SECURE=true
```

For local testing, copy `.env.example` to `.env`, set:

```text
DATABASE_URL=sqlite:///local.db
SESSION_COOKIE_SECURE=false
PUBLIC_BASE_URL=http://127.0.0.1:5000
```

Install and run:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py init-db
python manage.py create-test-key --order-id LOCAL-001 --name "One hour test" --hours 1
python app.py
```

Open `http://127.0.0.1:5000` and enter the generated key.

Run automated tests:

```bash
python -m unittest discover -s tests -v
```

## G2G API access

Request OpenAPI/API Integration access from the same G2G seller account that owns the listings. After approval, store the API key, API secret, and seller user ID in Render:

```text
G2G_API_KEY=
G2G_API_SECRET=
G2G_USER_ID=
```

Do not create or commit a `.env` file containing those secrets.

## Product duration mapping

Create one G2G offer for each subscription duration. Put the exact G2G offer IDs in `G2G_PRODUCTS_JSON`.

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

Enter the JSON as a single line in Render:

```text
G2G_PRODUCTS_JSON={"REAL_OFFER_ID_30D":{"name":"Software access - 30 days","duration_days":30},"REAL_OFFER_ID_90D":{"name":"Software access - 90 days","duration_days":90}}
```

Each offer defaults to a maximum order quantity of one. This prevents one purchase event from being ambiguously treated as multiple subscriptions.

## Webhook

Set the G2G webhook URL to:

```text
https://your-render-service.onrender.com/webhooks/g2g
```

Subscribe to:

```text
order.api_delivery
order.cancelled
order.refunded
```

Create a webhook secret and set:

```text
G2G_WEBHOOK_SECRET=<same webhook secret>
G2G_WEBHOOK_CANONICAL_URL=https://your-render-service.onrender.com/webhooks/g2g
```

The canonical URL must match exactly, including HTTPS, path, and trailing slash.

## Enable automation

After the local key test and webhook signature test pass, set:

```text
G2G_INTEGRATION_ENABLED=true
```

Redeploy.

For `order.api_delivery`, the app:

1. verifies the webhook signature;
2. checks that `seller_id` matches your G2G user ID;
3. looks up the `offer_id` in `G2G_PRODUCTS_JSON`;
4. generates a random buyer key;
5. saves the purchase and expiration;
6. calls the G2G Deliver Code endpoint;
7. sends the software provider, login email, software password, portal URL, buyer key, and exact expiration time.

The order ID is unique, so webhook retries reuse the same key instead of creating duplicates.

## Expiration and revocation

Expiration is checked on every portal request. A scheduled job is not required to stop access.

Optional database housekeeping:

```bash
python manage.py expire-orders
```

Manual revocation:

```bash
python manage.py revoke-order --order-id "G2G_ORDER_ID"
```

Refund and cancellation webhook events revoke the matching order automatically.

## Important deployment notes

- The repository may remain public only because no real secret is committed.
- Keep the Render environment values private.
- Use PostgreSQL, not Render's temporary filesystem.
- Confirm your software account permits the number of simultaneous users you intend to sell.
- Test a short one-hour offer before selling long durations.
- Test refund handling before enabling automatic delivery.
- G2G can update API payload details. If G2G's current developer console shows a different delivery path, set `G2G_DELIVERY_PATH_TEMPLATE` without editing code.
