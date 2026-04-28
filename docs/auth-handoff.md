# `auth` branch — handoff

Written for the next chat (on `main` or the next subsystem branch) picking up after auth Phase 1 lands.

## TL;DR

`auth` Phase 1 introduces Django auth + the Space / SpaceMembership schema. Login is required for every view; a Personal Space is auto-created on User creation; existing data is backfilled to a seed user. Functionally still single-user — Phase 2 (`spaces` branch) adds invites, multi-member Spaces, opt-in/out UI, and a Space switcher. Signup is invite-only — no public registration form ships.

## Run it

```bash
git checkout claude/gracious-swirles-dba1f6   # or wherever Phase 1 ended up
source .venv/bin/activate
python manage.py migrate
python manage.py createsuperuser   # if no users yet — see "Backfill" below
python manage.py runserver
```

Sign in at http://127.0.0.1:8000/login/ . Everything else (`/`, `/accounts/`, `/transactions/`, `/goals/`, `/admin/`) requires authentication. Logout is `/logout/`.

## What's in the branch

- **New `auth_app/` app** — `Space`, `SpaceMembership` models; login/logout views (`AppLoginView`, `AppLogoutView` thin wrappers around Django built-ins); `post_save` signal on `User` that creates a Personal Space + SpaceMembership.
- **`Space` model** — `name`, `owner` (User FK), `is_personal` (bool, partial-unique with owner), `accounts` (M2M → `accounts.Account`), `created_at`. Has a `transactions_qs()` helper returning the queryset of transactions on opted-in accounts. Phase 1 auto-opts every account into its owner's Personal Space; the M2M is the seam Phase 2 will use for selective opt-in.
- **`SpaceMembership` model** — `space`, `user`, `joined_at`; `unique_together(space, user)`.
- **`current_space(user)` helper** — Phase 1 returns the user's single Personal Space; Phase 2 will read from session (Space switcher).
- **Owner FKs** — `Account.owner` and `Goal.owner` are required `ForeignKey(User, on_delete=CASCADE)`. Migrations land them as nullable, the backfill data migration assigns owners, then `AlterField(null=False)` tightens the schema. Six migrations total across three apps:
  - `accounts/0003_account_owner.py` — adds nullable owner
  - `accounts/0004_alter_account_owner.py` — flips to NOT NULL
  - `goals/0002_goal_owner.py` — adds nullable owner
  - `goals/0003_alter_goal_owner.py` — flips to NOT NULL
  - `auth_app/0001_initial.py` — Space + SpaceMembership + M2M
  - `auth_app/0002_backfill.py` — data migration (see "Backfill" below)
- **View scoping** — every view is decorated with `@login_required`. Aggregation helpers (`dashboard.views._month_summary`, `_savings_over_time`, `_savings_goal_periods`; `goals.models.period_savings`) now take a `base_qs` parameter instead of calling `Transaction.objects` directly. The home / accounts / transactions views compute `base_qs = current_space(request.user).transactions_qs()` once and thread it through. Goals views filter `Goal.objects.filter(owner=request.user)`; goal-detail and account-detail use `get_object_or_404(..., owner=request.user)` so cross-user access returns 404 (verified end-to-end).
- **Form scoping** — `TransactionForm.__init__(user=...)` limits the account dropdown to `Account.objects.filter(owner=user)`. `GoalForm.__init__(user=...)` scopes the basket-total validator to that user's existing goals.
- **Settings** — `LOGIN_URL=auth_app:login`, `LOGIN_REDIRECT_URL=dashboard:home`, `LOGOUT_REDIRECT_URL=auth_app:login`. `auth_app` added to `INSTALLED_APPS`.
- **Templates** — `templates/auth_app/login.html` (extends `base.html`); `templates/base.html` hides the bottom-nav for unauthenticated users.
- **Admin** — `Space` and `SpaceMembership` registered (Space uses `filter_horizontal` for the accounts M2M). `Account` / `Goal` admins gained an `owner` column + filter.

## Backfill

The data migration (`auth_app/0002_backfill.py`) handles existing dev DBs:

- **No users exist + no data exists**: noop. Fresh install.
- **No users exist + data exists** (the typical pre-auth state): creates a `seed` user with `set_unusable_password()`, claims all Account/Goal rows, creates the seed user's Personal Space, opts in every account. Dev runs `python manage.py changepassword seed` (or `createsuperuser --username seed` if it already exists) to be able to log in.
- **Users already exist**: picks the first superuser as the claim-target. Every existing user (super or not) also gets their own Personal Space materialized, since the `post_save` signal only fires for users created *after* the migration runs.

The migration is reversible (sets owners back to NULL); the `AlterField(null=False)` follow-ups are reverted in turn by Django.

## Decisions this branch made

Recorded in CLAUDE.md as a single bullet under "Decisions" (the multi-tenancy direction itself was locked in earlier). The notable subdecisions:

1. **Scope at the Space level for shared aggregations, at the user level for goals and detail/mutation views.** Goals are private per `docs/security-plan.md` ("Each User privately owns their Goals"); transactions feed the Space's combined view. Account-detail goes through `owner=request.user` rather than the Space, so co-members can't reach the mutate-level UI even after Phase 2 lands the M2M-based list view.
2. **No public signup form in Phase 1.** Per `docs/security-plan.md`, signup is invite-only; the invite-token flow is Phase 2. Phase 1 ships login + admin-created users only.
3. **`post_save` signal is the only Personal-Space creation path in app code.** The migration backfills existing users explicitly because signals don't fire under `RunPython`. Going forward, every User creation route (admin form, `createsuperuser`, future invite acceptance) routes through the signal automatically.

## Open scope decisions still standing

These from CLAUDE.md are unchanged by this branch:

- **Phase 2 (separate `spaces` branch)** — invite-token signup, multi-member Spaces, opting accounts in/out, Space switcher UI. Schema is ready; no migration needed when Phase 2 starts.
- **Phase 3 (optional `spaces-roles`)** — admin / member / view-only roles.
- **Hosting target** — local-only. Per `docs/security-plan.md`, Phase 1 + hosting unblocks `plaid-sync` v2 (encrypted tokens, real Link).

## Suggested next steps (priority order)

1. **Merge `auth` → `main`.** Six migrations across three apps, end-to-end smoke-tested with two users. Run `python manage.py migrate` after pulling — the backfill is idempotent.
2. **Rebase any in-flight subsystem branches onto the new auth schema.** `Account` and `Goal` now require `owner`; views that touch them need `request.user`. `accounts`, `transactions`, `goals` views are already updated; any branch that forked before this needs to add `owner=request.user` to creates.
3. **Start `spaces` branch (Phase 2)** — invite tokens, multi-member, opt-in UI, Space switcher. Or `plaid-sync` v2 once a hosting target is picked.

## Notes on the code

- `current_space(user)` returns `None` if the user somehow has no Personal Space (shouldn't happen — the signal + migration cover every path — but the views handle it by falling back to empty querysets so a misconfigured user doesn't crash the home page).
- `Space` has a partial-unique constraint (`auth_app_one_personal_space_per_owner`) that lets a user own multiple non-personal Spaces (Phase 2/3) but only one Personal one.
- `SpaceMembership` is separate from `Space.owner` because Phase 2 lets one user own a Space and invite other members; Phase 1 only creates a single membership matching the owner.
- The login template is intentionally placeholder-styled like the rest of the app — design churn lives in `static/css/app.css`, structure should survive.
- Tests are still essentially empty (single-line `tests.py` files in every app). High-value targets when tests start landing: the post_save signal, `current_space` resolution, cross-user 404 on `account_detail` / `goal_detail`, and the form-level account dropdown scoping in `TransactionForm`.
