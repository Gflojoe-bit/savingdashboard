# `transfer-flag` branch — handoff

Written as a backfill after merge. Unlike prior subsystem handoffs this
work was done end-to-end in the same chat that did the merge, so there
was never an intermediate review point. Recording it here so future
chats discover the aggregation pattern without having to re-derive it.

## TL;DR

Two commits:

1. **Refactor** — aggregation math for income / spending / savings moves
   onto a `TransactionQuerySet` with `.in_range(start, end)` and
   `.summary()`. Single source of truth; both the home dashboard tile
   and the goals `net_savings()` helper now chain the same primitives.
2. **Fix** — new `Transaction.is_savings_transfer` boolean. A new
   manager method `.operational()` excludes flagged rows from
   aggregation. Transfers between user-owned accounts no longer
   inflate the income / spending tiles.

Shipped on `main`:

```
98482a9 Merge transfer-flag: aggregation refactor + savings-transfer exclusion
f5bc5cc Add Transaction.is_savings_transfer flag + .operational() exclusion
a5ec825 Refactor aggregation onto TransactionQuerySet manager
```

## What the double-count bug was

A transfer from checking → savings is two rows:

- checking: `amount = -500`
- savings:  `amount = +500`

Before the fix, both legs entered the home-dashboard summary:
- Income tile inflated by +500 (the savings leg).
- Spending tile inflated by +500 (the checking leg, sign-flipped).
- Savings tile = `income - spending` coincidentally still correct by
  symmetry — but only when both legs are recorded. If only the
  outbound leg is entered (because the destination account isn't
  tracked here), savings drops by 500 and the basket math under-allocates.

After the fix, aggregation chains `.operational()` to exclude
`is_savings_transfer=True` rows. Per-account `current_balance`
intentionally still includes transfers — they are real money
movements between accounts.

## New convention: the aggregation manager

Every site that computes income / spending / savings should use the
`TransactionQuerySet` (on `transactions/models.py`) rather than
reimplementing filters + aggregates. The canonical chain is:

```python
Transaction.objects.operational().in_range(start, end).summary()
```

- `.operational()` — exclude transfers. **Chain this first** on any
  aggregation path. Future filters (pending, refunds, …) land here.
- `.in_range(start, end)` — inclusive on both ends.
- `.summary()` — returns `{"income": Decimal, "spending": Decimal, "savings": Decimal}`.

Deliberate choice: `.operational()` is **opt-in**, not the default
manager. `Transaction.objects.all()` still returns every row so the
admin, `/transactions/`, and account detail views show transfers.
Exclusion is visible in every grep — missing `.operational()` calls
are the bug signal.

Policy (e.g. "net savings floored at 0" for goals) lives in the caller,
not the manager. The manager is plumbing only.

## Decisions this branch made

- **Single aggregation manager.** `TransactionQuerySet.summary()` is the
  one definition of income / spending / savings math. Removed from
  `dashboard/views.py` and `goals/models.py`.
- **Transfer flag is a boolean, not a category.** Considered
  `Transaction.category == "transfer"` but `category` is a Plaid-supplied
  free-text field and collisions with Plaid's own categories felt
  avoidable. A first-class boolean is ~10 lines, admin and form get a
  checkbox, future upgrade to a linked-`Transfer` model stays open.
- **Per-account `current_balance` keeps transfers.** Transfers are real
  movements between accounts. Only cross-account aggregations (home
  tiles, goal math) need the exclusion.

## Smoke test

From the branch commit, verified in the Django shell:

```
paycheck   +1000 (checking)
groceries  -200  (checking)
transfer   -500  (checking, is_savings_transfer=True)
transfer   +500  (savings,  is_savings_transfer=True)
```

- naive `.summary()`: income=1500, spending=700, savings=800
- `.operational().summary()`: income=1000, spending=200, savings=800
- per-account balances: checking=300, savings=500

Savings coincidentally matches either way (the transfer pair sums to 0).
The visible fix is the per-tile income / spending accuracy, and the
robustness against one-sided transfer entries.

## Open scope still standing

- **Refund problem.** A refund is `amount > 0` on a spending-category
  transaction — it inflates income rather than reducing spending.
  Not fixed here. Next filter that lands on `.operational()` will
  probably be a refund convention (`category == "refund"` or a second
  boolean).
- **Pending transactions** are included in aggregation. Plaid will
  surface pending rows; whether they belong in the tiles is undecided.
- **Date-range picker** on the home summary tile — scoped in this
  chat, not built. Default was discussed: rolling 30 days.
- **All period tiles become rolling** (1W / 1M / 3M) — scoped, not
  built. Belongs on a `rolling-periods` branch.

## Notes on the code

- Migration `transactions/0002_transaction_is_savings_transfer.py`
  adds the field with `default=False`, so existing rows are
  back-compat: behavior is unchanged until a row is flagged.
- Admin gets a column + list filter. Form at `/transactions/new/`
  gets a labeled checkbox ("Transfer between my accounts").
- The manager refactor is a pure no-op — `makemigrations --dry-run`
  was clean at the refactor commit, and `python manage.py check`
  passes at both.
- No tests yet; still a project-wide gap. High-value targets:
  `.summary()` math, `.operational()` exclusion, the form's checkbox
  round-trip.
- A smoke-test run in this chat wiped the local dev DB (two test
  accounts + four transactions). `db.sqlite3` isn't tracked, so
  nothing hit git — but any admin-entered data is gone. Re-seed on
  next `runserver`.
