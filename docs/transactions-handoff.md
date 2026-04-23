# `transactions` branch — handoff

Written for the next chat (on `main` or the next subsystem branch) picking up after transactions lands.

## TL;DR

`transactions` adds a real `Transaction` model and swaps every transaction- and balance-related placeholder on the home / accounts / transactions screens for real queries. The monthly income / spending / savings tiles are now computed. Goals-related UI is still stubbed (that's the `goals` subsystem's job). One commit ahead of `main`.

## Run it

```bash
git checkout transactions
source .venv/bin/activate
python manage.py migrate
python manage.py runserver
```

Add transactions at http://127.0.0.1:8000/admin/ under **Transactions**, or via the form at http://127.0.0.1:8000/transactions/new/. They'll immediately show up on `/`, `/accounts/<id>/`, and `/transactions/`, and `Account.current_balance` reflects them.

## What's in the branch (1 commit ahead of `main`)

```
02868c2 Add transactions subsystem: real Transaction model replaces fake data
```

- **New `transactions/` app** with `Transaction` model — fields: `account` (FK → `Account`), `date`, `amount` (signed Decimal: positive = income, negative = spending), `description`, `external_id`, `pending`, `merchant`, `category`, `created_at`. `is_credit` / `amount_abs` properties for display.
- **Migration** — `transactions/migrations/0001_initial.py` creates `transactions_transaction`.
- **Admin** — `Transaction` registered with list, filter (account, pending, category), search (description, merchant, external_id), date hierarchy.
- **`Account.current_balance` property** (`accounts/models.py`) — `balance + sum(transactions.amount)`. `balance` itself stays as the starting-balance snapshot.
- **Routes** — `/transactions/` and `/transactions/new/` live in `transactions/urls.py`, included from `config/urls.py`. The old `dashboard:transactions` URL name is gone; nav and home both use `transactions:list`.
- **Dashboard aggregation swapped** — `dashboard/views.py::home` now computes `month_summary` (income / spending / savings for the current month) from real rows and pulls the 3 most recent transactions. `account_detail` reads `account.transactions.all()`. Balance displays on home table, `/accounts/`, and `/accounts/<id>/` use `current_balance`.
- **CLAUDE.md** — new "Decisions" section records the two decisions this branch resolved (see below). Those two bullets were removed from "Not yet decided."

## Decisions this branch made

Both moved from CLAUDE.md's "Not yet decided" list into a new **Decisions** section:

1. **`Account.balance` is a starting-balance snapshot**, not the source of truth. `current_balance` is a computed property (`balance + sum(transactions)`). Chosen because Plaid returns a balance directly and CSVs rarely reach account open — a pure computed balance would require a synthetic opening transaction per account.
2. **Transaction `amount` is signed** (positive = income, negative = spending). No separate `type` field. Matches bank CSV / Plaid conventions; the dashboard month tiles split via `amount__gt=0` / `amount__lt=0`.

## Plaid readiness (intentional, currently unused)

Per the Plaid note in CLAUDE.md, the model includes four fields that sit empty until/if a Plaid or importer sync path exists:

- `external_id` (unique, nullable) — provider-side ID, for dedup.
- `pending` (bool) — unsettled transaction flag.
- `merchant` (str) — provider-supplied merchant name.
- `category` (str) — provider-supplied category.

Manual entries leave all four blank. The `TransactionForm` only exposes the four fields a human fills in (`account`, `date`, `amount`, `description`).

## What's still on fake data

Only goals-related items. Everything else now reads real rows.

| fake_data name | Still fake | Owner subsystem |
|---|---|---|
| `GOALS` | yes | `goals` |
| `SAVINGS_GOAL_PERIODS` | yes | `goals` (and the W/M/Y target decision) |

Transaction-shaped fake data (`TRANSACTIONS_BY_ACCOUNT`, `TRANSACTIONS_BY_MONTH`, `RECENT_TRANSACTIONS`, `TOTAL_SAVINGS`, `MONTH_SUMMARY`) is no longer referenced by any view. The constants still live in `dashboard/fake_data.py` — safe to delete, left in place to keep the diff focused. Consider removing when `goals` lands.

## Open scope decisions still standing

These from CLAUDE.md are unchanged by this branch:

1. **Weekly/Monthly/Yearly savings target** — needed for the goal tile on home. Decide in `goals` or via a settings field.
2. **"Savings over time" chart data source** — snapshot table vs compute on the fly. Revisit when wiring Chart.js; with real transactions, computing on the fly is now a live option.
3. **Where accounts/goals list-detail views live long-term.** Transactions moved to its own app; accounts list/detail is still in `dashboard/`. CLAUDE.md suggests moving them when those subsystems next get touched.

## Suggested next steps (priority order)

1. **Merge `transactions` → `main`.** One commit, verified end-to-end against a running server.
2. **Start `goals` subsystem** — define `Goal` model, replace `fake_data.GOALS`, and settle the W/M/Y target question (powers the goal tile on home).
3. **Chart + importer + auth + design** — same order as the dashboard-ui handoff. The "savings over time" chart now has real `Transaction` history to compute against.
4. **Cleanup** — once `goals` is real, delete `dashboard/fake_data.py` entirely.

## Notes on the code

- `_month_summary()` in `dashboard/views.py` takes an optional `today` arg — useful if tests want to freeze the clock.
- `Transaction.Meta.ordering = ["-date", "-created_at"]` — so same-day manual entries sort by insertion. Relied on by the home "recent 3" slice and the grouped-by-month list.
- `TransactionForm` uses `<input type="date">` — works on mobile but falls back to a plain text field on older desktop browsers.
- No tests yet; still a gap. A few high-value targets: `current_balance` math, `_month_summary()` income/spending signs, and the form's redirect on save.
- `.claude/launch.json` gained a `django` preview config, but the Claude Preview sandbox can't currently read the `.venv` — use `python manage.py runserver` manually. The config is harmless; leave or delete.
