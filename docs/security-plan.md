# Security plan for Plaid integration

Written before applying to Plaid Development tier. Captures the
plan in one place so the Plaid application form is a copy-paste, and
so the implementation order is clear.

## Context

- **Use case**: single-user personal savings dashboard. The "user" is
  the developer (me).
- **Data sensitivity**: Plaid `access_token`s are forever-credentials
  to read bank-account data. Treated as crown jewels.
- **Today's state**: no auth, no HTTPS, sandbox-only data shape doc
  (see `docs/plaid-data-shape.md`). No real bank data anywhere yet.
- **Goal**: lay out the minimum-viable security posture for a
  single-user personal app holding real bank read access.

## Threat model

In scope (what this plan defends against):

- Stolen / lost laptop with the `.env` file or DB on disk
- Accidental commit of secrets to git (already mitigated by `.gitignore`)
- Compromised host or container in production
- Plaid's webhook endpoint being hit by random internet traffic
- Code-level information leakage (logging an `access_token` by accident)

Out of scope:

- Targeted attacks against this specific user
- Compromise of Plaid itself
- Compromise of the bank itself
- Hardware-level attacks against the host
- Family-member-borrowing-laptop class threats (assume sole user
  controls the device)

## Plan by concern

| Concern | Plan | Implementation |
|---|---|---|
| **Access-token storage** | Encrypted at rest with Fernet (symmetric AES-128-CBC + HMAC-SHA256). | New `PlaidItem` model in `plaid_sync/`. Encrypted field via `django-fernet-fields` or a thin wrapper around `cryptography.fernet`. |
| **Encryption key** | Single env var `PLAID_TOKEN_ENCRYPTION_KEY`. In `.env` locally; in host secret manager in prod. **Never** in git, **never** in DB. | Bootstrap: `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`. |
| **Key rotation** | Rotate the encryption key by re-encrypting all rows in a single management command, then dropping the old key from the host. | Management command: `python manage.py rotate_plaid_key --new-key ...`. |
| **HTTPS in transit** | Required for any non-sandbox use. Plaid refuses HTTP for production webhooks. | Hosting platform provides Let's Encrypt automatically (Fly.io / Railway / Render — all $5/mo tier). HSTS enabled via `SECURE_HSTS_SECONDS`. |
| **Authentication** | Django built-in `auth`. Single user, long random password from a password manager. | The `auth` subsystem (already on the roadmap). Required before any Development-tier traffic. |
| **2FA** *(optional)* | `django-otp` for TOTP, **or** rely on hosting platform's SSH/admin 2FA if app is behind Tailscale / private network. | Defer until after first deploy unless the app goes public. |
| **Database at rest** | SQLite is acceptable for single-user personal use. Rely on the host's disk-level encryption (default on every modern PaaS). Backups encrypted in the same way. | No code change. Document that SQLite is intentional and migrate to Postgres only if multi-user happens. |
| **Webhooks** | Plaid signs every webhook with a JWT. Endpoint is public but rejects any request whose signature doesn't verify against Plaid's published JWKS. | Webhook handler in `plaid_sync/views.py`. Use Plaid's published verification helper. Stub (raise 401 on every request) before real wiring. |
| **Logging** | Never log `access_token`, full request/response bodies, or merchant-level transaction strings. Log API errors with structured redaction. | A `logging.Filter` that redacts `access_token` and any field starting with `access-` from log records. |
| **Secrets in source control** | `.env` is in `.gitignore`. CI must read keys from environment, not files. PR-time secret scanner (`gitleaks` or GitHub's built-in scanner) catches accidental commits. | Already mostly in place. Add a pre-commit hook for `gitleaks` when CI lands. |
| **Disposal — single Item** | When unlinking a Plaid Item: call Plaid `/item/remove`, then delete the encrypted token row. | Admin action + management command. Run before deleting from local DB. |
| **Disposal — full app** | Revoke every Item via `/item/remove`, drop the encryption key from the host, delete the database. | Documented runbook. No code. |
| **Incident response** | If access token is suspected compromised: (1) `/item/remove` for the affected Item, (2) rotate `PLAID_TOKEN_ENCRYPTION_KEY`, (3) force re-link via Plaid Link, (4) audit access logs for the incident window. | Documented runbook. Maybe a `manage.py panic` command later. |

## Sample answers for Plaid's Development application

These can be copy-pasted into the application form once the
implementation lands.

> **How do you store access tokens?**
>
> Encrypted at rest using Fernet (AES-128-CBC with HMAC-SHA256) via
> the `cryptography` Python library. The encryption key is held in
> the host's secret manager, separate from the database. Plaintext
> tokens exist only in memory during request processing and are never
> written to logs.

> **Is your application HTTPS-only?**
>
> Yes. TLS via Let's Encrypt, terminated at the hosting platform's
> ingress. HSTS is enabled. HTTP requests redirect to HTTPS.

> **Authentication method?**
>
> Django's built-in session-based authentication. Single-user
> deployment.

> **Where is the application hosted?**
>
> [Fly.io / Railway / Render] in [region]. Single-tenant.

> **Who has access to the data?**
>
> Only the authenticated user (the application owner — me).

> **Data retention?**
>
> Retained while the user account is active. On account deletion,
> all linked Plaid Items are revoked via `/item/remove`, and all
> transactions, accounts, and access tokens are deleted from the
> local database.

> **Third-party data sharing?**
>
> None. No analytics, no third-party crash reporting, no LLM
> processing on transaction data.

> **Incident response plan?**
>
> If a token is suspected compromised: revoke the affected Plaid
> Item via `/item/remove`, rotate the encryption key, force re-link
> via Plaid Link, audit access logs for the incident window.

> **What user-facing data does the application display?**
>
> Account names, balances, transaction histories, and aggregations
> (income / spending / savings) computed from those transactions.
> No identifying information beyond what Plaid returns.

## Build order

Each row gates the next.

| # | Step | Gates |
|---|---|---|
| 1 | **`plaid-sync` v1** — sandbox-only, management command, runs locally with `.env` keys. No auth required, no encryption required. | Nothing — start now. |
| 2 | **This document** committed and reviewed. | Plaid Development application. |
| 3 | **`auth` subsystem** — Django built-ins, login required for all views. | Production traffic. |
| 4 | **Hosting setup** — pick a platform, deploy with HTTPS. | Production traffic. |
| 5 | **`plaid-sync` v2** — encrypted `PlaidItem` storage, real Plaid Link flow, webhook endpoint with signature verification. | Plaid Development tier (real banks). |
| 6 | **Plaid Development tier application** — submit using the answers above. Approval ~2 weeks. | Real banks. |
| 7 | **Real bank link** — exercise the full pipeline against actual data. | Plaid Production tier (later, if ever). |

Steps 3 and 4 can run in parallel with 6 (Plaid approval is async).

## Open items

- **Hosting platform.** Fly.io vs. Railway vs. Render — all viable.
  Pick when step 4 starts; not a Plaid-blocking decision.
- **Webhook URL strategy in dev.** Plaid sandbox webhooks need a
  public URL. Options: ngrok tunnel during dev, or skip webhooks
  entirely in v1 and poll `/transactions/sync` on a cron. Decide in
  the `plaid-sync` v1 chat.
- **Backup policy.** No backups today. If/when one is added, it must
  be encrypted (the host's encrypted-at-rest backup is fine; an
  off-site copy without encryption is not).
- **Secret scanner.** `gitleaks` or GitHub's secret scanner — pick
  when CI is set up. Both are free.
- **Audit log.** Currently the only "audit log" is the host's request
  logs. For a single-user personal app this is acceptable. Revisit
  if multi-user happens.

## Notes

- **This plan is a security floor, not a ceiling.** Single-user
  personal use does not require everything a multi-tenant SaaS
  would. If the project ever takes on additional users, revisit
  every row of the table — particularly authentication, audit
  logging, and per-user encryption-key isolation.
- **None of this blocks the sandbox build.** Steps 1 and 2 happen
  in parallel; the build chat can ship `plaid-sync` v1 against
  sandbox data while this doc is being reviewed.
