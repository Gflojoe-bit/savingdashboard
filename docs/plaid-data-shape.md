# Plaid Sandbox — data shape findings

One-off exploration on `plaid-explore` branch. Goal: see what real Plaid sandbox JSON looks like before deciding how to map it onto our `Transaction` / `Account` models. **No model changes here, no merge to main.** The script (`scripts/plaid_explore.py`) and dumps (`scripts/plaid_dump/`, gitignored) can be regenerated any time.

## Setup

- Sandbox `client_id` + `secret` in `.env` (gitignored). `PLAID_ENV=sandbox`.
- No new Python dependencies — stdlib `urllib` + `json`. Skipped the `plaid-python` SDK because this is throwaway.
- Institution: `ins_109508` ("First Platypus Bank"), the canonical sandbox bank — gives a varied set of account types out of the box.

## API flow (4 calls)

```
/sandbox/public_token/create   → public_token
/item/public_token/exchange    → access_token, item_id
/accounts/get                  → list of accounts on the item
/transactions/sync  OR  /transactions/get  → transactions
```

In production the first call is replaced by Plaid Link (browser flow, returns a `public_token`). Everything from `/item/public_token/exchange` onward is identical across sandbox and production.

### `/transactions/sync` vs `/transactions/get`

- **`/sync`** is the modern cursor-based endpoint. Returns `added` / `modified` / `removed` lists relative to the cursor; first call (`cursor=""`) returns the full initial state. **Has a warm-up:** first call after item creation returns `transactions_update_status: "NOT_READY"` with empty lists. Poll until status flips to `INITIAL_UPDATE_COMPLETE` (recent ~30 days) and ideally `HISTORICAL_UPDATE_COMPLETE` (full backfill, up to 24 months). On our sandbox run, INITIAL returned 16 rows; HISTORICAL added 0 more, but `/transactions/get` over a 2-year window returned 388 — so for sandbox the historical pull happens lazily.
- **`/get`** is the older endpoint. Takes explicit `start_date` / `end_date`, paginated by `count` + `offset`. No warm-up gating — returns whatever's available immediately. Returned 388 transactions over a 2-year window in our test.

For our use case, **`/sync` is the right primary endpoint** (cursor handles dedup automatically and surfaces deletes/edits — both things our manual-entry model doesn't currently handle). `/get` is useful for one-off backfills and exploration.

## Accounts (`/accounts/get`)

Plaid's First Platypus Bank gives **12 accounts** spanning every major type:

| `type`       | `subtype`         | name                       | current balance |
|--------------|-------------------|----------------------------|----------------:|
| depository   | checking          | Plaid Checking             | 110             |
| depository   | savings           | Plaid Saving               | 210             |
| depository   | cd                | Plaid CD                   | 1,000           |
| depository   | money market      | Plaid Money Market         | 43,200          |
| depository   | hsa               | Plaid HSA                  | 6,009           |
| depository   | cash management   | Plaid Cash Management      | 12,060          |
| credit       | credit card       | Plaid Credit Card          | 410             |
| credit       | credit card       | Plaid Business Credit Card | 5,020           |
| investment   | ira               | Plaid IRA                  | 320.76          |
| investment   | 401k              | Plaid 401k                 | 23,631.98       |
| loan         | student           | Plaid Student Loan         | 65,262          |
| loan         | mortgage          | Plaid Mortgage             | 56,302.06       |

### Account JSON shape

```json
{
  "account_id": "kB3kPK3VRVUn8xxeyMQ9fLa5RlRbyEuLnqBMl",
  "balances": {
    "available": 100,
    "current": 110,
    "limit": null,
    "iso_currency_code": "USD",
    "unofficial_currency_code": null
  },
  "holder_category": "personal",
  "mask": "0000",
  "name": "Plaid Checking",
  "official_name": "Plaid Gold Standard 0% Interest Checking",
  "subtype": "checking",
  "type": "depository"
}
```

### Notes for our `Account` model

- We have `Account.type` already; Plaid's `type` is broader (`depository / credit / loan / investment`) and `subtype` is what most users actually identify with (`checking / savings / credit card / mortgage`). If we add Plaid sync, we'll likely want to store both, or store `subtype` and derive `type`.
- `balances.current` is the money-in-account number we care about. `balances.available` is current minus pending — useful but not what we display today.
- `mask` is the last-4 digits — nice for disambiguating "Chase Checking" from "Chase Checking" in the UI.
- Loan and credit balances are positive numbers in Plaid (you owe `56,302.06` on the mortgage, not `-56,302.06`). Our `credit-cards` subsystem will need to decide the sign convention here. Likely: store the raw Plaid number and apply sign at display time based on `type`.

## Transactions

### Single transaction JSON (full shape)

```json
{
  "account_id": "kB3kPK3VRVUn8xxeyMQ9fLa5RlRbyEuLnqBMl",
  "account_owner": null,
  "amount": 5.4,
  "iso_currency_code": "USD",
  "unofficial_currency_code": null,

  "date": "2026-04-14",
  "datetime": null,
  "authorized_date": "2026-04-13",
  "authorized_datetime": null,

  "name": "Uber 063015 SF**POOL**",
  "merchant_name": "Uber",
  "merchant_entity_id": "eyg8o776k0QmNgVpAmaQj4WgzW9Qzo6O51gdd",
  "logo_url": "https://plaid-merchant-logos.plaid.com/uber_1060.png",
  "website": "uber.com",

  "pending": false,
  "pending_transaction_id": null,
  "transaction_id": "XJvB6ZvL3LH3rZZm174jsAXkKG3GZ8ubdoway",
  "transaction_type": "special",
  "transaction_code": null,
  "payment_channel": "online",

  "personal_finance_category": {
    "primary": "TRANSPORTATION",
    "detailed": "TRANSPORTATION_TAXIS_AND_RIDE_SHARES",
    "confidence_level": "VERY_HIGH",
    "version": "v2"
  },
  "personal_finance_category_icon_url": "https://plaid-category-icons.plaid.com/PFC_TRANSPORTATION.png",

  "category": null,
  "category_id": null,

  "counterparties": [
    {
      "name": "Uber",
      "type": "merchant",
      "entity_id": "eyg8o776k0QmNgVpAmaQj4WgzW9Qzo6O51gdd",
      "logo_url": "https://plaid-merchant-logos.plaid.com/uber_1060.png",
      "website": "uber.com",
      "phone_number": null,
      "confidence_level": "VERY_HIGH"
    }
  ],

  "location": {
    "address": null, "city": null, "region": null,
    "postal_code": null, "country": null,
    "lat": null, "lon": null, "store_number": null
  },

  "payment_meta": {
    "by_order_of": null, "payee": null, "payer": null,
    "payment_method": null, "payment_processor": null,
    "ppd_id": null, "reason": null, "reference_number": null
  }
}
```

### Sign convention — **opposite to ours**

This is the single most important finding for mapping.

- **Plaid:** `amount > 0` = money leaving the account (debit / spending). `amount < 0` = money entering the account (credit / refund / deposit).
- **Ours:** `amount > 0` = income. `amount < 0` = spending. (See CLAUDE.md "Decisions".)

Sandbox sample: 388 transactions, 340 positive (spending in Plaid's convention), 48 negative. We will need to **negate `amount`** at import time so our existing `.summary()` / `.operational()` math keeps working without changes. Document this clearly at the import boundary.

> Side note: the bank-CSV "convention" CLAUDE.md cites isn't universal. Many real-bank CSVs *do* match Plaid (positive = debit), some match us (positive = credit), and a few use two columns. The CSV importer (when built) will need a per-source sign toggle anyway; Plaid is just the first concrete case forcing the issue.

### Categorization

Plaid v1 categories (`category` / `category_id`) are deprecated and came back `null` in this run. Use `personal_finance_category`:

- `primary` — coarse bucket. Sandbox showed 9 distinct values: `FOOD_AND_DRINK`, `GENERAL_MERCHANDISE`, `LOAN_PAYMENTS`, `PERSONAL_CARE`, `RENT_AND_UTILITIES`, `TRANSFER_IN`, `TRANSFER_OUT`, `TRANSPORTATION`, `TRAVEL`.
- `detailed` — fine-grained (e.g. `TRANSPORTATION_TAXIS_AND_RIDE_SHARES`).
- `confidence_level` — `VERY_HIGH` / `HIGH` / `MEDIUM` / `LOW` / `UNKNOWN`.

Our `Transaction.category` is a free-text `str`. Easiest mapping: store `personal_finance_category.primary` as the value. We may eventually want a separate `category_detailed` field, but not now.

### Transfers — Plaid surfaces them, we filter them

Plaid's `TRANSFER_IN` / `TRANSFER_OUT` primary categories map directly to our `is_savings_transfer` flag. **Mapping rule:** if `personal_finance_category.primary` starts with `TRANSFER_`, set `is_savings_transfer=True`. This is much cleaner than detecting transfers from CSV descriptions. Edge case: an external transfer (out of the user's known accounts) probably *shouldn't* be flagged — but we can't tell from a single side of the transaction alone. Defer.

### Pending

Sandbox returned 0 pending transactions in our pull, but the field exists. CLAUDE.md flags pending handling as undecided. When we wire Plaid, simplest is to import them as-is (with `pending=True` on our model — already exists) and let `.operational()` decide whether to filter. Plaid also supplies `pending_transaction_id` to thread the pending → posted lifecycle, which we'd want to honor on subsequent `/sync` calls (the posted version `modifies` the pending one).

### Dates

Two date fields: `date` (posted date) and `authorized_date` (when the swipe/charge happened). Use `date` for our `Transaction.date` — that's what bank statements show. `datetime` and `authorized_datetime` were both `null` in sandbox; per Plaid docs they're only populated for some institutions.

## Mapping to our `Transaction` model

Our existing fields (from `transactions/models.py` / handoff doc):

| Our field            | Plaid source                                   | Notes                                          |
|----------------------|------------------------------------------------|------------------------------------------------|
| `account` (FK)       | `account_id` → `Account.external_id` lookup    | Need an `Account.external_id` field too        |
| `date`               | `date`                                         | Use posted date, not authorized                |
| `amount`             | **`-amount`**                                  | Sign flip — Plaid debit-positive → ours        |
| `description`        | `name`                                         | Long form ("Uber 063015 SF**POOL**")           |
| `external_id`        | `transaction_id`                               | Already on the model, ready for this           |
| `pending`            | `pending`                                      | Direct                                         |
| `merchant`           | `merchant_name`                                | Direct (cleaner than `name`)                   |
| `category`           | `personal_finance_category.primary`            | Free-text already; just store the string       |
| `is_savings_transfer`| `primary in ("TRANSFER_IN", "TRANSFER_OUT")`   | Heuristic; refine later for external transfers |

**No model migration needed.** Everything we'd want from Plaid maps onto fields the `transactions` subsystem already added (per the Plaid-readiness section of `transactions-handoff.md`). The only new field would be `Account.external_id` for the account-side join.

Things Plaid gives us that we'd **drop** for now:

- `logo_url`, `personal_finance_category_icon_url` — UI nicety, defer.
- `counterparties[]` — richer than `merchant_name` but redundant for v1.
- `location` — null in sandbox anyway; privacy-sensitive in prod.
- `payment_meta`, `payment_channel`, `transaction_type/code` — interesting but not used by any current view.
- `personal_finance_category.detailed` / `.confidence_level` — could matter for the AI projection layer (Phase 2). Keep in mind, don't store yet.
- `iso_currency_code` — we're USD-only. Worth a sanity check at import (skip non-USD with a warning) but not a stored field.
- `authorized_date`, `datetime` fields — null-heavy and we don't have a use.

## Open questions surfaced by this exploration

1. **Account-side identity.** `Account` doesn't have `external_id` today. Adding it is trivial (nullable str, unique-or-not) but it's the minimum-viable model change for Plaid sync. Decide if/when to add.
2. **Initial-import scope.** `/sync` gives us recent + cursor for incremental, `/get` gives us up to 24 months in one shot. Bootstrapping a new account: probably one `/get` for backfill, then `/sync` from then on. Or just `/sync` with patience while HISTORICAL fills in.
3. **Refund handling.** A negative-amount Plaid transaction with a *spending* category (e.g. `TRAVEL` for the United Airlines `-$500` row in our sandbox) is the refund convention CLAUDE.md flagged as "probably wrong" in our model. Plaid surfaces this naturally; we still don't have a refund convention to map *into*. The two questions are now linked.
4. **Sandbox transfer realism.** The sandbox includes `TRANSFER_IN` / `TRANSFER_OUT` rows on the same item — but a real cross-account transfer between two of *the user's* accounts (the case we built `is_savings_transfer` for) only becomes detectable when we have multiple Plaid items linked or when both sides happen within one item. The single-side flagging rule above will over-flag external transfers (paying a friend, ACH out to a 401k held elsewhere). Acceptable v1.
5. **Webhook story.** None of this used webhooks. Real Plaid usage triggers `SYNC_UPDATES_AVAILABLE` webhooks rather than polling. Ignored for the explore; needs a public URL to even test.

## Reproducing this

```bash
# .env must have PLAID_CLIENT_ID and PLAID_SECRET
python3 scripts/plaid_explore.py
# dumps land in scripts/plaid_dump/ (gitignored)
```

The script is ~100 lines, stdlib only, idempotent — each run mints a fresh sandbox item. Safe to delete the script and dump dir once we've made the import-vs-CSV decision.
