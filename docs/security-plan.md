# Security plan for Plaid integration

Written before applying to Plaid Development tier. Captures the
plan in one place so the Plaid application form is a copy-paste, and
so the implementation order is clear.

## Context

- **Use case**: a private, **invite-only** financial tracker for a
  small trusted group (developer + spouse + family members + possibly
  business partners). Up to ~10 users at the high end. Membership is
  controlled exclusively by the owner — no public signup. Architected
  on a "Space" primitive: each user owns their data privately, and
  Spaces are combined views that members opt their accounts into.
- **Data sensitivity**: Plaid `access_token`s are forever-credentials
  to read bank-account data. Treated as crown jewels. **Each token is
  scoped to the User who linked it** — never shared across users,
  even among Space co-members.
- **Today's state**: no auth, no HTTPS, sandbox-only data shape doc
  (see `docs/plaid-data-shape.md`). Plaid sandbox sync ships data
  into local SQLite (no real bank data yet). The `auth` subsystem is
  next — Phase 1 lands the Space schema and login (functionally
  single-user); Phase 2 lands invites and multi-member; Phase 3 is
  optional roles.
- **Goal**: lay out the minimum-viable security posture for an
  invite-only multi-tenant personal app holding real bank read access.

## Threat model

In scope (what this plan defends against):

- Stolen / lost laptop with the `.env` file or DB on disk
- Accidental commit of secrets to git (already mitigated by `.gitignore`)
- Compromised host or container in production
- Plaid's webhook endpoint being hit by random internet traffic
- Code-level information leakage (logging an `access_token` by accident)
- **Cross-user data leakage** — a Space co-member seeing accounts the
  owner didn't opt in. Defended via per-account opt-in (the Space
  primitive itself), per-User Plaid Items, and queryset scoping by
  `request.user` everywhere.

Out of scope:

- Targeted attacks against specific users in the trusted group
- Compromise of Plaid itself
- Compromise of the bank itself
- Hardware-level attacks against the host
- Member-of-the-trusted-group going rogue (the model assumes Space
  co-members are mutually trusted; per-account opt-in mitigates the
  blast radius if trust is misplaced, but doesn't prevent a determined
  bad-actor co-member from screenshotting what they can already see)

## Plan by concern

| Concern | Plan | Implementation |
|---|---|---|
| **Access-token storage** | Encrypted at rest with Fernet (symmetric AES-128-CBC + HMAC-SHA256). | New `PlaidItem` model in `plaid_sync/`. Encrypted field via `django-fernet-fields` or a thin wrapper around `cryptography.fernet`. |
| **Encryption key** | Single env var `PLAID_TOKEN_ENCRYPTION_KEY`. In `.env` locally; in host secret manager in prod. **Never** in git, **never** in DB. | Bootstrap: `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`. |
| **Key rotation** | Rotate the encryption key by re-encrypting all rows in a single management command, then dropping the old key from the host. | Management command: `python manage.py rotate_plaid_key --new-key ...`. |
| **HTTPS in transit** | Required for any non-sandbox use. Plaid refuses HTTP for production webhooks. | Hosting platform provides Let's Encrypt automatically (Fly.io / Railway / Render — all $5/mo tier). HSTS enabled via `SECURE_HSTS_SECONDS`. |
| **Authentication** | Django built-in `auth`. Each user has their own login, long random password from a password manager. **Invite-only signup** — a new user must present a valid invite token (admin-issued) to create an account. No public registration form. | The `auth` subsystem Phase 1 (login + Space schema) and Phase 2 (invite tokens, multi-member Spaces). Phase 1 required before any Development-tier traffic. |
| **Per-user data isolation** | Every `Account`, `Goal`, and Plaid Item belongs to exactly one User. Spaces are combined *views*, not shared *ownership* — a Space's accounts are the union of opt-ins from each member, but each account is still owned (and only mutable) by its individual User. Every queryset is scoped by `request.user` (for personal views) or by Space membership + per-account opt-in (for shared views). | Manager methods on each model (e.g. `Account.objects.visible_to(user)`) so the filter logic lives in one place. |
| **Cross-user Plaid Items** | Plaid `access_token`s are User-scoped. A Space co-member never sees another user's tokens, only the *accounts* the other user opted into the Space. | Enforced at the model level — `PlaidItem.user` FK is non-null, no Space FK on `PlaidItem`. |
| **2FA** *(optional)* | `django-otp` for TOTP, **or** rely on hosting platform's SSH/admin 2FA if app is behind Tailscale / private network. | Defer until after first deploy unless the app goes public. |
| **Database at rest** | SQLite is acceptable for the trusted-group scale (~10 users). Rely on the host's disk-level encryption (default on every modern PaaS). Backups encrypted in the same way. Migrate to Postgres if scale or concurrency demand it (likely never for this use case). | No code change. Document that SQLite is intentional and revisit only if a real bottleneck appears. |
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
> Django's built-in session-based authentication. **Invite-only**
> signup — new users require an admin-issued invite token to register.
> No public signup form. Up to ~10 users (developer + spouse + family
> members) in a trusted group.

> **Where is the application hosted?**
>
> [Fly.io / Railway / Render] in [region]. Single-tenant — the entire
> application instance is owned and operated by me; "users" of the
> app are members of my trusted group, not customers.

> **Who has access to the data?**
>
> Each user sees only their own accounts, goals, and Plaid Items by
> default. Users may opt specific accounts into shared **Spaces** to
> combine views with co-members; each account is opted in explicitly
> by its owner. Plaid `access_token`s are never visible to anyone but
> the user who linked the bank — even Space co-members see the
> *accounts*, not the tokens.

> **Data retention?**
>
> Retained while the user account is active. On account deletion,
> all of that user's linked Plaid Items are revoked via `/item/remove`,
> and all of their transactions, accounts, goals, and access tokens
> are deleted from the local database. Spaces they were the sole
> member of are deleted; Spaces with remaining members lose only
> that user's contributed accounts.

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
| 3 | **`auth` Phase 1** — Space + SpaceMembership schema, signup auto-creates Personal Space, every view scoped to current Space. Login required for all views. Functionally single-user. | Production traffic for a single user. |
| 3b | **`auth` Phase 2** (separate `spaces` branch) — invite-token signup, multi-member Spaces, opting accounts in/out, Space switcher UI. | Trusted-group production traffic. |
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
  logs. For a trusted-group personal app this is acceptable. Revisit
  (a) if Spaces gain non-mutual-trust members or roles, or (b) if any
  data-sensitive action ever needs an after-the-fact paper trail.
- **Per-user encryption-key isolation.** Today, all users share one
  `PLAID_TOKEN_ENCRYPTION_KEY`. Tokens are still User-scoped at the
  row level via FK, so a code bug would have to fail queryset scoping
  *and* leak a row to expose someone else's token. For a trusted
  group this is acceptable. If the user count grows or trust assumptions
  weaken, move to per-User keys (key derived from a master + per-User
  salt).

## Notes

- **This plan is a security floor, not a ceiling.** A small trusted
  group does not require everything a public multi-tenant SaaS would.
  If the project ever opens to public signup, revisit every row of
  the table — particularly authentication (add email verification +
  MFA), audit logging (real records, not just host logs), per-user
  encryption-key isolation, and abuse-prevention (rate limiting,
  CAPTCHA on signup, device fingerprinting on login).
- **None of this blocks the sandbox build.** Steps 1 and 2 happen
  in parallel; the build chat can ship `plaid-sync` v1 against
  sandbox data while this doc is being reviewed.
