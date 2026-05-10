# Savings Dashboard

A Django app to track savings — accounts, transactions, goals, and a dashboard with charts.

## Stack

- Python 3.9 + Django 4.2 LTS
- SQLite (dev)
- Django templates + Chart.js (planned) for the dashboard UI
- stdlib `venv` at `.venv/`

## Setup

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py runserver
```

## Workflow: one branch + one chat per subsystem

Each major subsystem lives on its own branch and is developed in its own Claude chat. This keeps conversations focused and avoids context churn. `main` is the integration branch — merge subsystem branches in when they're ready.

When starting a chat on a subsystem branch, the first thing to do is read this file and the subsystem's scope below.

## Subsystems (branches)

| Branch | Scope |
|---|---|
| `auth` | **Phase 1**: Django auth + `Space` / `SpaceMembership` schema; signup auto-creates a Personal Space; existing data backfilled to a seed Space; every view scoped to current Space. Functionally single-user, but with the right schema. **Phase 2** (separate branch `spaces`): invite flow, multi-member Spaces, opting accounts in/out, Space switcher UI. **Phase 3** (optional `spaces-roles`): admin / member / view-only roles. |
| `accounts` | Bank/savings account records — name, type, institution, current balance. Model + admin + basic CRUD views. |
| `transactions` | Deposits/withdrawals/transfers tied to an account. Model + list/create views. Source of truth for balances (derived via sum). |
| `goals` | Savings targets — name, target amount, target date, linked account(s). Progress calculation. |
| `dashboard` | Home view: totals, recent activity, progress charts (Chart.js). Read-only aggregation layer. |
| `plaid-sync` | Plaid integration: `Account.external_id`, `/transactions/sync` import, sign-flip + transfer detection per `docs/plaid-data-shape.md`. Sandbox first; Development/Production tier later. |
| `credit-cards` | `Account.type = credit` choice + `charged_to_cards()` queryset disaggregation. Surfaces credit-card spending as data piped to home and as a `?type=credit` filter on the transactions list. **Out of scope:** Bill model and tracker → `bill-tracker` branch; Net Worth banner / Savings/Debt split / credit detail view → deferred to UX redesign. |
| `bill-tracker` | Bill model (due dates, statement balance, paid_on), bills list view, urgency-colored bills strip on home, checking→card payment form. Discoverability of credit-card obligations. |

## Conventions

- Project folder (settings + root URLs) is `config/`. Apps live at the repo root alongside it.
- App per subsystem: `auth_app/`, `accounts/`, `transactions/`, `goals/`, `dashboard/`, `importer/` (Django reserves `auth` and `import`).
- Migrations are committed.
- Keep subsystem branches small and mergeable — rebase on `main` before merging.

## Decisions

- **`Account.balance` is a starting-balance snapshot**, with `current_balance` computed as `balance + sum(transactions.amount)`. Chosen because Plaid gives a balance directly and CSV imports rarely go back to account open — a pure computed balance would force a synthetic opening transaction per account.
- **Transaction `amount` is signed**: positive = income, negative = spending. Matches bank CSV / Plaid conventions; dashboard tiles split via `sum(positive)` / `sum(negative)` rather than a separate `type` field.
- **Goals use a basket-allocation model.** Each `Goal` has a `basket_percent` (0–100); deposits aren't tied to specific goals individually, instead net savings (income − spending) is split across goals by basket weight. Per-goal saved = `net_savings × basket_percent / 100`. Basket must sum to 100% (validated in form). Chosen for v1 to sidestep "pick a target date OR pick a contribution cadence" — both fall out as derived projections. **Note: this is a v1 UX commitment and is expected to evolve** once real use surfaces mismatches (e.g. one-off contributions like "put $500 in vacation this month" aren't naturally expressible under basket-only math). Revisit once the per-category contribution-form decision in "Not yet decided" is made.
- **Goal progress is computed lazily**, not stored. No allocation table; recompute on every page load from the current basket × cumulative net savings. Trade: changing the basket retroactively rewrites past progress. Acceptable for MVP; an `Allocation` snapshot table can land later if real history is needed.
- **Home goal tile = aggregate, rolling 1W / 1M / 3M.** Saved = net savings in that rolling window ending today; target = sum of all goal targets. Not per-goal. See `docs/rolling-periods-handoff.md`.
- **Savings is retrospective.** Every aggregation window looks backward from today — there is no forward projection in the base math. Future-dated transactions aren't counted as savings until their date arrives. Forecasts / projections are a separate layer (see AI projection in "Not yet decided"). This is why the rolling tile dropped "year": calendar-to-date semantics conflict with "past N days".
- **Home summary tiles (Income / Spending / Savings) are calendar-month**, not rolling. Calendar windows reset-and-grow, which is motivating; rolling windows are stable signal. Different UX jobs, both kept. Do not "normalize" without a UX conversation.
- **Net savings floored at 0.** If a period's spending exceeds income, the period contributes nothing to goals — you can't distribute negative savings. Implemented in `goals.models.net_savings()`.
- **Goal creation requires `basket_percent`.** The new-goal form validates that the total basket across all goals equals 100% before saving — if not, the form rejects with a hint showing how much room is available. Existing goals must be rebalanced via `/goals/basket/` first to free up space.
- **Transaction.is_savings_transfer flag + `.operational()` aggregation manager.** Transfers between user-owned accounts are excluded from income / spending / savings math (they'd otherwise inflate both sides of the summary tiles). Every aggregation site chains `Transaction.objects.operational()` before `.summary()`. Per-account `current_balance` intentionally still includes transfers — they are real money movements. Future filters (pending, refunds, …) go on `.operational()`. See `docs/transfer-flag-handoff.md`.
- **No CSV importer subsystem.** Plaid covers the forward-looking sync; for one-off historical backfill (banks Plaid doesn't cover, or pre-2024 statements), a ~100-line `python manage.py import_csv path/to/file.csv` management command can be written ad-hoc when actually needed. Skipping the full subsystem (UI column mapping, preview, dedup workflow) avoids real engineering for a use case we don't have. The `import` row was removed from the subsystems table.
- **`plaid-sync` v1 = sandbox-only management command.** `python manage.py plaid_pull` mints (or reuses via `--access-token` / `PLAID_ACCESS_TOKEN`) a sandbox item, upserts accounts by `Account.external_id` (= Plaid `account_id`), and upserts transactions by `Transaction.external_id` (= Plaid `transaction_id`). All mapping rules from `docs/plaid-data-shape.md` apply at this single import boundary: sign-flip (`amount = -plaid.amount`), `is_savings_transfer` set when `personal_finance_category.primary` starts with `TRANSFER_`, posted `date` (not `authorized_date`), `category` = primary string. Sandbox returns 12 accounts spanning depository/credit/loan/investment; **v1 imports only depository checking + savings** (the only `Account.type` choices today) and skips the rest with a warning — credit/loan/investment land on the `credit-cards` subsystem. No `PlaidItem` model and no token encryption — both are explicitly v2 per `docs/security-plan.md`, gated on the `auth` subsystem and a hosting target.
- **Savings-over-time chart = absolute cumulative, computed on the fly.** One running total per day from the first operational transaction forward; range buttons (1W / 1M / 3M / 1Y / All) zoom the visible X-window while the Y values stay anchored to real cumulative totals. Chart.js from CDN, full series shipped to the client and sliced client-side on zoom. No snapshot table — (b) from the old "data source choice" bullet. Chart does NOT floor at 0 (that's a goals-side allocation rule; the chart's job is to tell the truth). Transfers excluded via `.operational()`. See `docs/chart-handoff.md`.
- **Space-based multi-tenancy** (replaces the earlier single-user-vs-multi-user open question). Each `User` privately owns their `Account`s, `Goal`s, and (eventually) Plaid Items. A `Space` is a combined view: members opt in specific accounts, and the Space dashboard shows the union. Each user is auto-given a Personal Space on signup; couples create a shared Space and each opt in the joint accounts they want surfaced; family-beyond-couple (parents, in-laws) live in their own Spaces, fully isolated; an S-corp owner can stand up one Space per business and an aggregate "empire" Space combining the lot. Strictly more flexible than a Household model — every Household scenario is just a Space with N members opting in everything. Privacy is per-account opt-in, not per-Space-member. Phasing: Phase 1 ships the schema + Personal Space auto-create (functionally single-user); Phase 2 ships invites + multi-member; Phase 3 ships roles. See the `auth` subsystem row above. Signup is invite-only; no public registration.
- **`auth` Phase 1 — Django auth + Space schema, no public signup.** Login is required for every non-admin view (`@login_required` on each view, `LOGIN_URL=auth_app:login`). The `auth_app` app owns `Space`, `SpaceMembership`, login/logout views, and a `post_save` signal on `User` that auto-creates a Personal Space + SpaceMembership for every new user — guarantees the "every user has exactly one Personal Space" invariant for any creation path (admin, `createsuperuser`, future invite flow). `Account.owner` and `Goal.owner` are required FKs to `User` (a data migration backfills existing rows onto a seed user — first existing superuser, else a `seed` user with unusable password). `Space.accounts` is a M2M for per-account opt-in; Phase 1 auto-opts every new account into the user's Personal Space. View scoping: `current_space(user)` returns the Personal Space (Phase 1 has exactly one); `space.transactions_qs()` is the base queryset all aggregation helpers (`_month_summary`, `_savings_over_time`, `period_savings`) now take as a parameter. Goals scope by `owner=user` directly (private to the user, never opted into a Space — see `docs/security-plan.md`); account-detail and goal-detail views use `get_object_or_404(..., owner=request.user)` so co-members can't reach mutate-level views even if Phase 2 lands. Signup is invite-only; the `auth_app` ships no public registration form — admin creates users via `/admin/` until the Phase 2 invite flow lands. See `docs/auth-handoff.md`.
- **Month-over-month delta lines on home summary tiles.** Each summary tile (Income / Spending / Savings) shows a "+$140.00 vs last month" line below the value. Comparison is MTD-to-MTD (same-day-of-month windowing), not partial-vs-full, so the delta is a fair pace signal. Hidden when the prior-month window is empty. Coloring is single muted tone — directional red/green deferred until design tokens land.
- **`dev-fixtures` — `python manage.py seed_demo`** for local dev data. Generates a demo user with 4 accounts (checking, savings, 2 credit), ~12 months of varied transactions including transfer pairs, and 4 balanced goals. Idempotent via `external_id="demo:*"` keys. `--reset` to wipe and re-seed. Bails out if `DEBUG=False`. Not run in production; intended for design + screenshot + eyeballing workflows.
- **`credit-cards` shipped narrow.** Original plan in `docs/credit-cards-handoff.md` covered the Bill model, net-worth math, IA changes (Net Worth banner, Savings/Debt split), and a credit-detail view. Final ship was just `Account.type=credit` + `TransactionQuerySet.charged_to_cards()` disaggregation feeding a (not-yet-rendered) home tile, plus a `?type=credit` filter on the transactions list. Bill tracking moved to its own subsystem (`bill-tracker`); IA changes and credit-detail view deferred to the UX redesign pass. The shipped `charged_to_cards` tile is *not* net worth — it's "card spending this period," a disaggregation of the existing spending number, not an additional subtraction from savings.

## Not yet decided

- Deployment target (local-only for now).
- Whether to go past `plaid-sync` v1 (sandbox-only, no auth, no encryption) to v2 (real Plaid Link, encrypted token storage, webhook). Gated on `auth` Phase 1 + hosting per `docs/security-plan.md`.
- **AI projection layer for goals** (Phase 2). Once there's ~2-3 months of transactions, suggest realistic completion dates per goal and surface basket-rebalance suggestions to hit `target_date`. Not built in v1.
- **Per-category amount/date contribution form** (open question from goals chat). Two interpretations: (a) the goal-edit form gains an optional "save $X every month" recurring contribution alongside the basket %, or (b) a separate manual allocation form for one-off "$100 → vacation on Apr 15" entries that bypass the basket. Quite different implementations; deferred until decided.
- **Goal edit + delete views.** Currently admin-only. Once a goal is created, its name/category/target/date can only be changed via `/admin/`. Add inline edit/delete UI when goals UX matters more.
- **Where subsystem views live long-term.** Transactions and goals moved to their own apps (`transactions/`, `goals/`); accounts list/detail is still in `dashboard/`. Rule going forward: home stays in `dashboard/` (aggregation); each subsystem's list/detail moves to its owning app when that subsystem is next touched.
- **Refund convention.** A refund today is `amount > 0` on a spending-category transaction — it inflates income rather than reducing spending. Probably wrong. Next filter to land on `.operational()` will likely be a refund flag / category.
- **Pending transactions** are included in aggregation. Plaid surfaces pending rows; whether they belong in the summary tiles is undecided.
- **Direction-aware coloring of delta lines** (income up = green, spending up = red, savings up = green). Deferred until design tokens land so the colors come from variables.
- **Desktop width cap.** Layout is mobile-first with no max-width — stretches full-width on desktop. Add a `max-width` later if it bothers anyone.
- **When to bring in a professional designer** — the current look is intentionally placeholder. Structure should survive a redesign; mostly `static/css/app.css` churn.
