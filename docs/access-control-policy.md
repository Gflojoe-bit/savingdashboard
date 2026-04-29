# Access Control Policy

**Document owner:** Joseph Gorenflo (sole developer / operator)
**Effective date:** 2026-04-29
**Version:** 1.0
**Review cadence:** On material change to the application or its hosting

## 1. Purpose

This policy establishes how access to the Savings Dashboard
application's production assets and sensitive data is controlled.
It covers end-user authentication, administrative access, and
service-to-service credentials including Plaid `access_token`s and
the encryption key that protects them.

## 2. Scope

This policy applies to:

- Production environment (hosting platform, application server, database)
- Application source code repository (private)
- End-user data: account metadata, transaction history, Plaid
  `access_token`s, savings goals
- Administrative credentials: host login, Plaid dashboard, encryption key

## 3. Identity and roles

The application currently operates at solo-developer scale with two
distinct identity classes:

- **Operator (1):** the sole developer / application owner. Holds
  administrative access to all systems.
- **End users (≤ ~10):** the developer's spouse and trusted family
  members. Hold authenticated access to their own data only.

Phase 3 of the application will introduce admin / member / view-only
roles within shared Spaces. Until then, every end user has equivalent
permissions on their own data.

## 4. Access principles

- **Least privilege.** End users see only their own accounts,
  transactions, and goals by default. Cross-user visibility is
  opt-in per account, never automatic.
- **No public signup.** Account creation is invite-only. Invite
  tokens are admin-issued and single-use.
- **Per-user data isolation.** Every domain model (`Account`, `Goal`,
  `PlaidItem`) has an `owner` foreign key to a User. Every queryset
  filters on `owner = request.user` for personal views, or by Space
  membership + per-account opt-in for shared views.
- **Service credentials are scoped.** Plaid `access_token`s are tied
  to a single User. They are encrypted at rest with Fernet (AES-128-CBC
  + HMAC-SHA256) and never logged.

## 5. Authentication

- **End users:** Django session-based authentication with username
  and password. Strong passwords managed via password manager.
- **Operator:** Hosting platform login with MFA required. The
  encryption key is held in the host's secret manager, separate
  from the database.
- **Service-to-service:** OAuth-pattern `access_token`s for Plaid;
  TLS certificates (Let's Encrypt) for HTTPS termination.

## 6. Authorization

- Every Django view is decorated with `@login_required`. Anonymous
  access is denied.
- Detail and mutation views additionally scope by
  `owner = request.user`, returning 404 (not 403) on cross-user
  access attempts.
- Aggregation views scope to the user's current Space, and within
  that Space, to opted-in accounts only.

## 7. Provisioning and revocation

- **Provisioning.** Invite-only signup (Phase 2). The operator
  generates an invite token; the recipient redeems it to create
  an account.
- **Revocation.** When an end user is removed:
  1. All of that user's Plaid Items are revoked via Plaid
     `/item/remove`.
  2. All of the user's data (accounts, transactions, goals,
     encrypted tokens) is deleted from the database.
  3. The user's Spaces are either deleted (sole-member) or lose
     only the user's contributed accounts (multi-member).
- **Operator key rotation.** Encryption keys are rotated on
  suspected compromise via a documented management command that
  re-encrypts all stored tokens with the new key.

## 8. Review and audit

- **Periodic reviews.** Not formally scheduled at solo-developer
  scale. Informal review on every material change to the security
  plan, with all changes captured in version control.
- **Audit log.** The hosting platform's request logs serve as the
  operational audit trail. A dedicated application-level audit
  log is a documented future enhancement.

## 9. Document owner and version control

This policy is committed to the project repository under version
control. Changes require a commit and are visible in the
repository's history. The document owner is responsible for
keeping this policy aligned with the application's actual
practices.

## Cross-references

- `docs/security-plan.md` — broader security plan with threat model,
  per-concern mitigations, and Plaid Development application sample
  answers.
- `docs/auth-handoff.md` — implementation notes for the Phase 1 auth
  subsystem that operationalizes this policy.
