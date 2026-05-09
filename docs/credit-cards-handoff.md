# `credit-cards` subsystem handoff

**Branch:** `credit-cards` (created from `main` at f690a27)
**Status:** Not started — this doc is the planning artifact. Read it, then build.

Per CLAUDE.md convention, this subsystem gets its own chat. First step in that chat: read `CLAUDE.md` and this doc.

## Scope

Add credit card accounts, scheduled bills with due dates, and a checking → card payment flow. Introduces a savings / debt / net worth split on the dashboard. **No Plaid liability data** — that lands in `plaid-sync` v2.

## Schema

### `Account.TYPE_CHOICES`
Add `("credit", "Credit Card")`. Migration is choices-only, no data change.

### `Account.balance` semantics for credit accounts
Same starting-balance snapshot model as checking/savings, but a **positive balance means "you owe this much."** Display layer flips the sign / framing for credit accounts; the underlying model stays uniform.

Sign convention is unchanged from the existing transaction model:
- **Spending on the card** → `Transaction.amount` is negative (matches bank/Plaid sign convention). For a credit account, this *adds to the debt*, so the absolute balance grows.
- **Card payment from checking** → two transactions, both `is_savings_transfer=True`:
  - On checking: `amount` negative (cash out)
  - On credit: `amount` positive (debt reduced — current_balance shrinks)

`current_balance` already includes transfers (see CLAUDE.md), which is what we want — paying down the card should reduce the displayed debt.

### New model: `Bill`
Lean toward putting it in `accounts/models.py` to avoid app sprawl. Justify a separate `bills/` app only if it grows.

```python
class Bill(models.Model):
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="bills"
    )
    due_date = models.DateField()
    amount_due = models.DecimalField(max_digits=12, decimal_places=2)  # statement balance
    min_payment = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    statement_close_date = models.DateField(null=True, blank=True)
    paid_on = models.DateField(null=True, blank=True)
```

Validate in `clean()` that `account.type == "credit"`. Properties: `is_paid`, `is_overdue`.

### No payment-link model
A "checking → credit payment" is just two `Transaction` rows with `is_savings_transfer=True`. The payment view creates the pair and sets `Bill.paid_on`. No join table.

## Aggregation

### Account queryset extensions
```python
class AccountQuerySet(models.QuerySet):
    def savings_assets(self):
        return self.filter(type__in=[Account.CHECKING, Account.SAVINGS])
    def debt(self):
        return self.filter(type=Account.CREDIT)
```

### `net_worth(user)` helper
```python
def net_worth(user):
    accounts = Account.objects.filter(owner=user)
    assets = sum((a.current_balance for a in accounts.savings_assets()), Decimal(0))
    debt = sum((a.current_balance for a in accounts.debt()), Decimal(0))
    return assets - debt
```

### `.operational()` already correct
Card payments are `is_savings_transfer=True` and drop out of income / spending / savings math automatically. **Write a test** that confirms a card payment leaves `period_savings` unchanged.

## Dashboard / IA changes

The home tile structure shifts. Today: Income / Spending / Savings + goals. After this branch:

| Section | Before | After |
|---|---|---|
| Top banner | — | **Net Worth** = assets − debt |
| Balance group | Account totals | Split rows: **Savings** (assets) and **Debt** |
| Calendar-month tiles | Income / Spending / Savings | Unchanged |
| Goals tile | Rolling 1W / 1M / 3M | Unchanged |
| Bills strip | — | Upcoming bills next 14 days, urgency-colored |
| Savings-over-time chart | Cumulative line | Unchanged (still operational-only) |

Goals math is unchanged — bill payments are transfers, already excluded from net savings.

## Views

Per CLAUDE.md ("subsystem views move to their owning app on next touch"), this branch also **moves the account list/detail views from `dashboard/` to `accounts/`**.

New views (all `@login_required`, scoped by `account.owner=request.user`):
- `accounts/credit/<id>/` — credit-card detail. Shows current balance, statement balance (from latest unpaid Bill), next due date, transaction list.
- `bills/` — list of upcoming + recently-paid bills.
- `bills/<id>/pay/` — payment form. Pick checking account, amount, date → creates the transfer pair, marks bill `paid_on`.

## Migrations

1. `accounts/00XX_add_credit_account_type.py` — choices-only addition.
2. `accounts/00XX_bill.py` — create Bill model.

Forward-only. No data migration needed (no credit accounts exist yet).

## Tests

Minimum coverage:
- Credit account creation; positive `current_balance` displays as debt.
- Card spend (negative txn) increases the displayed debt.
- Card payment (transfer pair) decreases displayed debt **and** is excluded from `period_savings`.
- `net_worth` = assets − debt.
- Bill: `is_paid`, `is_overdue` properties.
- Bill payment flow: form creates 2 transactions + sets `paid_on`.

## Out of scope

- Plaid liability data fetch (APR, statement close, min payment auto-populate) — `plaid-sync` v2.
- Reward category tracking, per-card spend limits, alerts.
- Multi-currency.
- Joint cards across Space members — covered when Spaces Phase 2 lands.

## Open questions for the implementing chat

- **Where does `Bill` live?** Lean: `accounts/models.py`. Could justify `bills/` app later.
- **Display: statement balance vs current balance** on credit detail — lean toward both, with statement balance as the primary "what you owe right now."
- **Urgency coloring threshold** for the bills strip — suggest red if overdue, amber if ≤ 3 days, default otherwise.
- **Bills strip on home: next bill only or all upcoming-14-days?** Lean: top 3, with "view all" link.

## When done, before merging to main

- Update CLAUDE.md "Subsystems" table row for `credit-cards` to reflect what shipped.
- Add a "Decisions" bullet capturing any non-obvious calls (e.g. where Bill lives, urgency thresholds).
- Move the "credit-cards" line out of "subsystem branches not started" in any tracking docs.
- Rebase on `main` before opening the merge.
