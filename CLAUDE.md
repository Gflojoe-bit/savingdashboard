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
| `auth` | User accounts, login/logout, registration, password reset. Uses Django's built-in `auth` app. |
| `accounts` | Bank/savings account records — name, type, institution, current balance. Model + admin + basic CRUD views. |
| `transactions` | Deposits/withdrawals/transfers tied to an account. Model + list/create views. Source of truth for balances (derived via sum). |
| `goals` | Savings targets — name, target amount, target date, linked account(s). Progress calculation. |
| `dashboard` | Home view: totals, recent activity, progress charts (Chart.js). Read-only aggregation layer. |
| `import` | CSV import of transactions. Column mapping, deduplication, preview-before-commit. |
| `credit-cards` | Credit card accounts (new `Account.type = credit`), scheduled bills with due dates, checking→card payment flow. Introduces savings / debt / net worth split on the dashboard. |

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
- **Savings-over-time chart = absolute cumulative, computed on the fly.** One running total per day from the first operational transaction forward; range buttons (1W / 1M / 3M / 1Y / All) zoom the visible X-window while the Y values stay anchored to real cumulative totals. Chart.js from CDN, full series shipped to the client and sliced client-side on zoom. No snapshot table — (b) from the old "data source choice" bullet. Chart does NOT floor at 0 (that's a goals-side allocation rule; the chart's job is to tell the truth). Transfers excluded via `.operational()`. See `docs/chart-handoff.md`.

## Not yet decided

- Deployment target (local-only for now).
- Multi-user vs single-user — start single-user, revisit.
- Whether to add Plaid or stay manual/CSV-only. Sandbox explored — see `docs/plaid-data-shape.md` for the full mapping. Headline findings: every Plaid transaction field maps onto fields the `transactions` subsystem already added (no model migration needed for transactions); only gap is `Account.external_id` for the account-side join. **Sign convention is opposite ours** (Plaid: positive=debit; ours: positive=income) — negate at import boundary. `TRANSFER_IN` / `TRANSFER_OUT` categories map directly to `is_savings_transfer`. Decision on whether to actually wire a `plaid-sync` subsystem still pending.
- **AI projection layer for goals** (Phase 2). Once there's ~2-3 months of transactions, suggest realistic completion dates per goal and surface basket-rebalance suggestions to hit `target_date`. Not built in v1.
- **Per-category amount/date contribution form** (open question from goals chat). Two interpretations: (a) the goal-edit form gains an optional "save $X every month" recurring contribution alongside the basket %, or (b) a separate manual allocation form for one-off "$100 → vacation on Apr 15" entries that bypass the basket. Quite different implementations; deferred until decided.
- **Goal edit + delete views.** Currently admin-only. Once a goal is created, its name/category/target/date can only be changed via `/admin/`. Add inline edit/delete UI when goals UX matters more.
- **Where subsystem views live long-term.** Transactions and goals moved to their own apps (`transactions/`, `goals/`); accounts list/detail is still in `dashboard/`. Rule going forward: home stays in `dashboard/` (aggregation); each subsystem's list/detail moves to its owning app when that subsystem is next touched.
- **Refund convention.** A refund today is `amount > 0` on a spending-category transaction — it inflates income rather than reducing spending. Probably wrong. Next filter to land on `.operational()` will likely be a refund flag / category.
- **Pending transactions** are included in aggregation. Plaid surfaces pending rows; whether they belong in the summary tiles is undecided.
- **Delta vs prior period** on calendar summary tiles ("$890 this month, +$140 vs last month") — cheap motivation boost, not built.
- **Desktop width cap.** Layout is mobile-first with no max-width — stretches full-width on desktop. Add a `max-width` later if it bothers anyone.
- **When to bring in a professional designer** — the current look is intentionally placeholder. Structure should survive a redesign; mostly `static/css/app.css` churn.
