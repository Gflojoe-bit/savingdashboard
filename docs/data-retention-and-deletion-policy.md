# Data Retention and Deletion Policy

**Document owner:** Joseph Gorenflo (sole developer / operator)
**Effective date:** 2026-04-29
**Version:** 1.0
**Review cadence:** On material change to the application, its
hosting, or applicable data-privacy law

## 1. Purpose

This policy specifies how long the Savings Dashboard application
retains personal and financial data, how that data is deleted on
user request or account closure, and how the policy stays aligned
with applicable data-privacy laws (GDPR, CCPA / CPRA, and similar
US state laws).

## 2. Scope

This policy applies to all personal and financial data stored or
processed by the application, including:

- **User identity:** username, hashed password, email address (if
  provided), Space memberships
- **Account metadata:** account names, types (checking / savings),
  institution names, balances, opt-in Space relationships
- **Transaction history:** transaction date, amount, description,
  merchant, category, pending flag, savings-transfer flag
- **Goals:** name, category, target amount, target date, basket
  percentage
- **Plaid Items:** access tokens (encrypted), item IDs, institution
  IDs, last-sync timestamps
- **Operational artifacts:** application logs, audit trails, error
  reports
- **Backups:** snapshots of any of the above held by the hosting
  platform

## 3. Retention periods

| Data category | Retention period |
|---|---|
| Active user account (all linked data) | Indefinite while the user account is active |
| Inactive user account (no login for 12 months) | Operator notifies the user; if no response within 30 days, the account is deleted per the deletion process below |
| Plaid `access_token`s | Until the user unlinks the corresponding Item, deletes their account, or the operator decommissions the app |
| Application request logs | Default retention of the hosting platform (typically 30–90 days) |
| Backup snapshots | Default retention of the hosting platform (typically 7–30 days) |
| Decommissioned / deleted user data | Removed from primary database immediately on deletion; expunged from backups within the next backup rotation cycle (≤ 30 days) |

No data is retained beyond the user's active relationship with the
application except where a backup rotation has not yet completed.

## 4. Deletion triggers

A deletion is initiated on any of the following events:

1. **User-initiated deletion.** The user requests account deletion
   from the application's settings interface (planned feature) or
   directly via the operator (until the in-app flow ships).
2. **Operator-initiated deletion.** The operator removes a user
   from the trusted group, e.g., when a family member leaves.
3. **Account dormancy.** The user has not logged in for 12 months.
   The operator notifies the user; absent a response in 30 days,
   the account is deleted.
4. **Application decommissioning.** The operator shuts down the
   application; all user data is deleted as part of teardown.
5. **Right-to-erasure request.** Any user, regardless of trigger,
   may request full deletion under GDPR Article 17, CCPA / CPRA
   right to delete, or equivalent state law. Such requests are
   honored within 30 days.

## 5. Deletion process

When a deletion is triggered, the following steps execute, in order:

1. **Revoke Plaid Items.** For each `PlaidItem` belonging to the
   user, call Plaid's `/item/remove` endpoint. This invalidates
   the `access_token` upstream.
2. **Delete Plaid Items locally.** The local `PlaidItem` row,
   including the encrypted `access_token`, is hard-deleted from
   the database.
3. **Cascade-delete owned data.** The user's `Transaction`,
   `Account`, `Goal`, and `SpaceMembership` rows are hard-deleted.
   `Account` and `Goal` foreign keys are configured with
   `on_delete=CASCADE`, so cascade is automatic.
4. **Resolve Spaces.** For each `Space` owned by the deleted user:
   - If the Space has only this user as a member, the Space is
     deleted.
   - If the Space has additional members, the Space remains, but
     the deleted user's contributed accounts are removed from it.
5. **Delete the User row.** The Django `User` row is hard-deleted.
6. **Backups.** The deletion propagates into the hosting
   platform's backup rotation. Snapshots taken before the deletion
   age out within ≤ 30 days; no manual scrubbing of historical
   backups is performed at this scale.
7. **Confirmation.** If the user requested deletion and provided an
   email address, the operator sends a confirmation email
   describing what was deleted and the backup-age-out window.

## 6. Compliance with applicable data-privacy laws

- **GDPR — right to erasure (Article 17).** Honored within 30 days
  of request; no data is retained after deletion except in
  age-out backups, which are explicitly disclosed.
- **GDPR — data portability (Article 20).** Users may request a
  data export (planned feature; until shipped, the operator
  provides the export manually on request).
- **GDPR — consent withdrawal (Article 7).** Withdrawing consent is
  equivalent to requesting deletion; no data is retained for
  marketing or analytics purposes (the application does neither).
- **CCPA / CPRA — right to delete.** Honored within 45 days
  (CCPA-required); the application's 30-day target meets this.
- **CCPA / CPRA — right to know.** Users may request a copy of
  the data the application holds about them; same path as GDPR
  data portability.
- **CCPA / CPRA — do-not-sell / do-not-share.** N/A — the
  application does not sell or share personal information with
  third parties for advertising or analytics.

## 7. Periodic review

Not formally scheduled at solo-developer scale. Review triggers:

- Material change to the application's data model or storage
- Material change to the hosting platform's backup retention
- New or amended data-privacy law (federal or state-level US,
  GDPR amendments, similar)
- Each material change to the broader security plan

## 8. Document owner and version control

This policy is committed to the project repository under version
control. Changes require a commit and are visible in the
repository's history. The document owner is responsible for
keeping this policy aligned with the application's actual deletion
behavior and with the prevailing legal landscape.

## Cross-references

- `docs/security-plan.md` — broader security plan with threat
  model, per-concern mitigations, and Plaid Development application
  sample answers
- `docs/access-control-policy.md` — access control policy covering
  end-user and service-to-service authentication
- `docs/mfa-policy.md` — multi-factor authentication policy for
  operator access to critical systems
