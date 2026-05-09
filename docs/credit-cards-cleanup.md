# `credit-cards` cleanup before merge

**Branch:** `credit-cards`
**Status:** Implementation slice landed in `7685b2a`. Three small items remain before merging into `main`. The original wide-scope plan in `docs/credit-cards-handoff.md` is **superseded** — this doc is now the source of truth for what's left.

## What shipped (already on the branch)

In commit `7685b2a` *("Pipe charged-to-cards tile data through home view context")*:

- `Account.CREDIT` choice + migration `accounts/migrations/0005_add_credit_account_type.py`
- `TransactionQuerySet.charged_to_cards()` queryset
- `_charged_to_cards_summary` calendar-month helper in `dashboard/views.py`, wired into home context as `charged_to_cards`
- Test coverage for the queryset and the helper

The home template is intentionally untouched — the data is piped through but no tile is rendered yet. That's by design; the rendering belongs to the UX redesign pass.

## What's left before merge

### 1. Add missing test: card payment does not move `period_savings`

This was called out in the original handoff but skipped. It locks in the rule that paying a credit card from checking is a transfer, excluded from operational/savings math.

Test sketch (in `transactions/tests.py`):

```python
def test_card_payment_does_not_change_period_savings(self):
    # Setup: user, checking acct, credit acct, baseline operational transactions
    # Compute period_savings_before
    # Create transfer pair:
    #   -X on checking (amount negative, is_savings_transfer=True)
    #   +X on credit   (amount positive, is_savings_transfer=True)
    # Compute period_savings_after
    # Assert before == after
```

Both rows of the transfer pair must have `is_savings_transfer=True`. Without that flag the operational queryset would treat them as real income/spending.

### 2. Add credit-card filter on the transactions list

Surface the existing `.charged_to_cards()` queryset to users.

**Where:** `templates/transactions/list.html` (full transactions list — most useful place for filters).

**UI:** simplest version — a single "Credit cards only" chip/toggle at the top of the list. Or filter chips: All / Credit cards / Bank. Pick the simpler one; this is a v1 surface.

**View change** (`transactions/views.py` — wherever the list view lives): accept a `?type=credit` query param and branch the queryset:

```python
qs = Transaction.objects.filter(account__owner=request.user)
if request.GET.get("type") == "credit":
    qs = qs.charged_to_cards()
```

**Test:** the filter param narrows the result set to credit-account transactions only. One assertion is enough.

### 3. Update CLAUDE.md

The `credit-cards` row in the **Subsystems** table currently describes the wide pre-implementation scope. Replace with what actually shipped:

> `credit-cards` | `Account.type = credit` choice + `charged_to_cards()` queryset disaggregation. Surfaces credit-card spending as data piped to home and as a filter on the transactions list. **Out of scope:** Bill model and tracker → `bill-tracker` branch; Net Worth banner / Savings/Debt split / credit detail view → deferred to UX redesign.

Add a row below it:

> `bill-tracker` | Bill model (due dates, statement balance, paid_on), bills list view, urgency-colored bills strip on home, checking → card payment form. Discoverability of credit-card obligations.

Add a bullet to the **Decisions** section:

> **`credit-cards` shipped narrow.** Original plan covered the Bill model, net-worth math, IA changes (Net Worth banner, Savings/Debt split), and a credit-detail view. Final ship was just `Account.type=credit` + `charged_to_cards()` disaggregation feeding a home tile and a transactions filter. Bill tracking moved to its own subsystem (`bill-tracker`); IA changes and credit-detail view deferred to the UX redesign pass.

## Out of scope — do not let these creep back in

- ❌ `Bill` model and any bill-tracking UI → `bill-tracker` branch.
- ❌ `AccountQuerySet.savings_assets()` / `.debt()` filters — skip until something needs them. Inline `filter(type__in=...)` is fine for now.
- ❌ `net_worth(user)` helper and the Net Worth banner on home → UX redesign. Note: the shipped `charged_to_cards` tile is *not* net worth; it's "card spending this period." Different number, different job.
- ❌ Savings / Debt split rows on home → UX redesign.
- ❌ Credit account detail view (`accounts/credit/<id>/`) → UX redesign / "connect accounts" surface.
- ❌ Move of account list/detail from `dashboard/` to `accounts/` → UX redesign.

## Merge prep

Once items 1–3 land:

1. Run the full test suite: `python manage.py test`.
2. Eyeball home in dev to confirm `charged_to_cards` is reachable from the template context (even though it isn't rendered).
3. Rebase on `main` if anything has landed there. (Probably hasn't.)
4. `git checkout main && git merge --no-ff credit-cards`.
5. `git push origin main`.

## Followup: `bill-tracker` subsystem

Open a `bill-tracker` branch + planning handoff afterward. The `Bill` model spec from `docs/credit-cards-handoff.md` is still the right starting point — copy it forward and expand on the UI surfaces (bills list, payment form, urgency-colored strip on home).
