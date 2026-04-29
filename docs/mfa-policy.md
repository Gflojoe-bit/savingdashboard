# Multi-Factor Authentication Policy

**Document owner:** Joseph Gorenflo (sole developer / operator)
**Effective date:** 2026-04-29
**Version:** 1.0
**Review cadence:** On material change to the operating environment or
hosting platform

## 1. Purpose

This policy specifies the multi-factor authentication (MFA) requirements
for operator access to all critical systems that store, process, or
provide administrative access to consumer financial data. It establishes
required factor types per system, enrollment expectations, and recovery
procedures.

End-user MFA on the consumer-facing application is governed separately
by `docs/access-control-policy.md`.

## 2. Scope

This policy applies to all systems that hold, process, or are capable
of accessing consumer financial data, including:

- **Hosting platform account** — production deployment, application
  logs, secret manager, and database access (added to scope at first
  deploy; not yet operational)
- **Source code repository (GitHub)** — application source, deployment
  configuration, encryption-key configuration
- **Plaid Dashboard account** — Plaid client credentials, item
  management, webhook configuration
- **Operator email account** — password reset destination for the
  systems above
- **Password manager** — credential store for all of the above
- **Operator workstation** — local development environment, including
  any locally-stored `.env` secrets

## 3. MFA requirement by system

The minimum required MFA factor for each in-scope system:

| System | MFA required | Factor type |
|---|---|---|
| Hosting platform (production, when deployed) | Yes | TOTP minimum; passkey or hardware security key preferred where supported |
| GitHub | Yes | Passkey (FIDO2 / WebAuthn) — phishing-resistant |
| Plaid Dashboard | Yes | TOTP |
| Operator email | Yes | Passkey (FIDO2 / WebAuthn) — phishing-resistant |
| Password manager | Yes | Master password + device biometric (Touch ID / Face ID) |
| Workstation login | Yes | Device biometric or strong password with full-disk encryption |

Where a system supports phishing-resistant MFA (passkeys, hardware
security keys, FIDO2 / WebAuthn), it is enabled in preference to
TOTP. For systems that do not yet offer phishing-resistant options
(currently the Plaid Dashboard), TOTP via an authenticator app is
the baseline.

SMS-based MFA is not used as a primary factor on any critical
system. Where SMS is offered alongside stronger factors, the
stronger factor is preferred.

## 4. Enrollment and enforcement

The operator is responsible for ensuring MFA is enrolled and active
on every account in scope. New critical systems added to the operating
environment trigger an MFA review before any consumer financial data
is stored or processed by them.

The hosting platform account is added to scope at the time of first
deploy. MFA enrollment on the hosting account is a deploy-blocker —
no real bank data is loaded into a hosted environment until MFA is
verified active on the operator's hosting account.

## 5. Recovery procedures

Loss of an MFA device or factor is handled per system:

- **Hosting platform / GitHub / Plaid / email** — each provides
  recovery codes generated at MFA enrollment. Recovery codes are
  stored in the password manager (which itself requires MFA).
- **Password manager** — Emergency Kit / recovery code stored
  offline in a secure physical location.
- **Operator workstation** — recovery via cloud account login +
  biometric on a backup device.

In the event of suspected MFA device theft or compromise, the
operator's playbook is to:

1. Revoke active sessions on every system in scope.
2. Re-enroll MFA on each affected system using a known-good device.
3. Rotate any secrets that may have been accessible to the lost
   session — including the Plaid token encryption key, per the
   incident response runbook in `docs/security-plan.md`.
4. Audit access logs for the incident window.

## 6. Periodic review

Not formally scheduled at solo-developer scale. Informal review
triggers:

- New device added to the operator's set (new laptop, new phone,
  new hardware security key)
- Replaced or lost hardware
- Material change to the systems-in-scope list (new critical
  service added, old service decommissioned)
- Each material change to the broader security plan
  (`docs/security-plan.md`)

## 7. Document owner and version control

This policy is committed to the project repository under version
control. Changes require a commit and are visible in the
repository's history. The document owner is responsible for
keeping this policy aligned with actual MFA enrollment status
across all in-scope systems.

## Cross-references

- `docs/security-plan.md` — broader security plan with threat model,
  per-concern mitigations, and Plaid Development application sample
  answers
- `docs/access-control-policy.md` — access control policy covering
  end-user and service-to-service authentication
