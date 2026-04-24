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

## Conventions

- Project folder (settings + root URLs) is `config/`. Apps live at the repo root alongside it.
- App per subsystem: `auth_app/`, `accounts/`, `transactions/`, `goals/`, `dashboard/`, `importer/` (Django reserves `auth` and `import`).
- Migrations are committed.
- Keep subsystem branches small and mergeable — rebase on `main` before merging.

## Decisions

- **`Account.balance` is a starting-balance snapshot**, with `current_balance` computed as `balance + sum(transactions.amount)`. Chosen because Plaid gives a balance directly and CSV imports rarely go back to account open — a pure computed balance would force a synthetic opening transaction per account.
- **Transaction `amount` is signed**: positive = income, negative = spending. Matches bank CSV / Plaid conventions; dashboard tiles split via `sum(positive)` / `sum(negative)` rather than a separate `type` field.
- **Goals use a basket-allocation model.** Each `Goal` has a `basket_percent` (0–100); deposits aren't tied to specific goals individually, instead net savings (income − spending) is split across goals by basket weight. Per-goal saved = `net_savings × basket_percent / 100`. Basket must sum to 100% (validated in form). Chosen for v1 to sidestep "pick a target date OR pick a contribution cadence" — both fall out as derived projections.
- **Goal progress is computed lazily**, not stored. No allocation table; recompute on every page load from the current basket × cumulative net savings. Trade: changing the basket retroactively rewrites past progress. Acceptable for MVP; an `Allocation` snapshot table can land later if real history is needed.
- **Home tile W/M/Y = aggregate**, not per-goal. Saved = net savings in that period; target = sum of all goal targets.
- **Net savings floored at 0.** If a period's spending exceeds income, the period contributes nothing to goals — you can't distribute negative savings. Implemented in `goals.models.net_savings()`.
- **Goal creation requires `basket_percent`.** The new-goal form validates that the total basket across all goals equals 100% before saving — if not, the form rejects with a hint showing how much room is available. Existing goals must be rebalanced via `/goals/basket/` first to free up space.

## Not yet decided

- Deployment target (local-only for now).
- Multi-user vs single-user — start single-user, revisit.
- Whether to add Plaid or stay manual/CSV-only. Current plan: Sandbox-first when we get there; transactions model should be shaped to accommodate Plaid fields (external_id, pending flag, merchant, category) to avoid a later migration.
- **"Savings over time" chart data source.** Either (a) a daily/weekly snapshot table of total-savings balance, or (b) compute on the fly from transaction history. Decide when wiring Chart.js.
- **AI projection layer for goals** (Phase 2). Once there's ~2-3 months of transactions, suggest realistic completion dates per goal and surface basket-rebalance suggestions to hit `target_date`. Not built in v1.
- **Savings-transfer flag on `Transaction`.** When the user moves money from checking to a savings account, it currently shows as spending in checking and inflates "spending" in `_month_summary` / shrinks net savings. Need a `is_savings_transfer` flag (or `category="transfer"` convention) so transfers are excluded from the income−spending math. Decide in `transactions` or here when it next gets touched.
- **Per-category amount/date contribution form** (open question from goals chat). Two interpretations: (a) the goal-edit form gains an optional "save $X every month" recurring contribution alongside the basket %, or (b) a separate manual allocation form for one-off "$100 → vacation on Apr 15" entries that bypass the basket. Quite different implementations; deferred until decided.
- **Goal edit + delete views.** Currently admin-only. Once a goal is created, its name/category/target/date can only be changed via `/admin/`. Add inline edit/delete UI when goals UX matters more.
- **Where subsystem views live long-term.** Currently all list/detail views sit in `dashboard/` against `fake_data.py`. Reasonable rule going forward: home stays in `dashboard/` (aggregation); accounts list/detail moves to `accounts/`; transactions to `transactions/`; goals to `goals/`. Confirm as each subsystem lands.
- **Desktop width cap.** Layout is mobile-first with no max-width — stretches full-width on desktop. Add a `max-width` later if it bothers anyone.
- **When to bring in a professional designer** — the current look is intentionally placeholder. Structure should survive a redesign; mostly `static/css/app.css` churn.
