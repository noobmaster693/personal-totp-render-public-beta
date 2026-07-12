# Personal TOTP — public Render beta

A minimal public TOTP display for a disposable test account. The page opens directly with no login. Render stores the permanent TOTP credential in the `TOTP_SECRET` environment variable and generates the current code server-side.

> **Important:** anyone who knows or discovers the Render URL can view the active code. This intentionally provides no access control and must never be used for an important or personal account.

## Deliberate restrictions

The website has no registration, login, QR scanner, secret importer, database, setup form, or secret-editing route. The only way to change the credential is through Render’s Environment page.

Routes:

- `/` — public code display
- `/api/code` — public JSON code endpoint
- `/health` — service health status

## GitHub contents

The public repository contains only source code. `.env` is ignored by `.gitignore`. Never commit a real TOTP secret, QR image, `otpauth://` URI, or `.env` file.

## Deploy with Render Blueprint

1. Create an empty GitHub repository and upload these files to its root.
2. In Render, choose **New → Blueprint** and connect the repository.
3. Render reads `render.yaml`.
4. Enter `TOTP_SECRET` when prompted.
5. Deploy and open the generated `onrender.com` URL.

`TOTP_SECRET` accepts either:

- A manual Base32 setup key
- A complete `otpauth://totp/...` URI

The included Blueprint tracks the `main` branch and uses `autoDeployTrigger: commit`, so pushes to `main` trigger a new Render deployment.

## Existing Render service

Open:

`Service → Environment → Edit`

Add:

| Key | Value |
|---|---|
| `TOTP_SECRET` | Disposable test account Base32 key or full `otpauth://` URI |
| `TOTP_LABEL` | Optional display label |
| `TOTP_ISSUER` | Optional issuer, such as `OpenAI` |

Select **Save, rebuild, and deploy**. The app reads the variable at process startup.

## Local test

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open `http://127.0.0.1:5000`.

## Tests

```bash
python -m unittest discover -s tests -v
```
