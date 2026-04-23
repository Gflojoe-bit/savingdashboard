# `accounts` branch — handoff

Written for the next chat (on `main` or the next subsystem branch) picking up after accounts lands.

## TL;DR

`accounts` replaces the home/accounts fake data with a real `Account` model. The UI is unchanged — same screens, same layout — but the rows now come from SQLite. One commit ahead of `main`.

## Run it

```bash
git checkout accounts
source .venv/bin/activate
python manage.py migrate
python manage.py runserver
```

Add accounts at http://127.0.0.1:8000/admin/ under **Accounts**. They'll appear on `/` and `/accounts/`.

## What's in the branch (1 commit ahead of `main`)

```
29d3099 Add accounts subsystem: real Account model replaces fake data
```

- **New `accounts/` app** with `Account` model — fields: `name`, `type` (choices: checking / savings), `institution`, `balance` (Decimal).
- **Migration** — `accounts/migrations/0001_initial.py` creates `accounts_account`.
- **Admin** — `Account` registered with list, filter, search.
- **Views swapped** — `home`, `accounts`, `account_detail` in `dashboard/views.py` read from `Account.objects.all()` / `get_object_or_404(Account, pk=...)`.
- **Templates** — use `{{ acct.get_type_display }}` so stored `"checking"` renders as `"Checking"`.
- **fake_data.py** — `ACCOUNTS` entry removed.

## What's still on fake data

Everything transactions/goals/totals related:

| fake_data name | Still fake | Owner subsystem |
|---|---|---|
| `TRANSACTIONS_BY_ACCOUNT` | yes | `transactions` |
| `TRANSACTIONS_BY_MONTH` | yes | `transactions` |
| `RECENT_TRANSACTIONS` | yes | `transactions` |
| `GOALS` | yes | `goals` |
| `TOTAL_SAVINGS` | yes | `transactions` (sum) |
| `MONTH_SUMMARY` | yes | `transactions` (income/spending split) |
| `SAVINGS_GOAL_PERIODS` | yes | `goals` or settings (see open scope in CLAUDE.md) |

## Open scope decisions still standing

These from `CLAUDE.md` are unchanged by this branch:

1. **Income vs spending split** — needed for `MONTH_SUMMARY`. Decide in `transactions`.
2. **Weekly/Monthly/Yearly target** — needed for the goal tile. Decide before finishing `goals`.
3. **"Savings over time" chart data source** — snapshot table vs compute on the fly.
4. **Where subsystem views live long-term** — accounts list/detail is currently still in `dashboard/`. CLAUDE.md suggests moving it to the `accounts/` app later; for now leaving it keeps the diff small.

## New decision this branch introduced

- **Balance is a stored field**, not computed. CLAUDE.md says the long-term source of truth for balances is the sum of transactions. For now, balance is a manually-entered `DecimalField` on `Account`. Once the `transactions` subsystem lands, either:
  - Remove `balance` from the model and compute via `sum(account.transactions)`, OR
  - Keep it as a snapshot / starting-balance field and add a computed `current_balance` property.
- Decide in the `transactions` chat.

## Suggested next steps (priority order)

1. **Merge `accounts` → `main`.** One small commit, no risk.
2. **Start `transactions` subsystem** — define `Transaction` with an FK to `Account`, swap the fake `TRANSACTIONS_*` entries, compute `TOTAL_SAVINGS` / `MONTH_SUMMARY` / `RECENT_TRANSACTIONS` from real data. This is also where the balance-computation decision above gets made.
3. **Then `goals`** — replace `fake_data.GOALS` and settle the W/M/Y target question.
4. **Then chart + importer + auth + design** — same order as the dashboard-ui handoff.

## Notes on the code

- `Account.TYPE_CHOICES` currently only has checking + savings. Credit/investment intentionally excluded per scope.
- `Account.institution` is optional (`blank=True`) — treat it as a display-only label.
- No tests yet; still a gap.
- `dashboard/views.py` still imports `Http404` — used by `goal_detail`, keep it.
