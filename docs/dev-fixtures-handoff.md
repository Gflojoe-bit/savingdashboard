# `dev-fixtures` handoff

**Branch:** `dev-fixtures` (created from `main` at `d7e0d2a`)
**Status:** Not started — this doc is the planning artifact.
**Audience:** A future Claude session implementing the seed-data tool.

First step in that chat: read `CLAUDE.md`, then this doc.

## Why this branch exists

The `ux-redesign` branch (parallel work) needs realistic data to design against. Empty/sparse screens look wrong even when the design is right. Seed data is genuinely **orthogonal to design** — it's a tool design uses, not a design artifact — so it lives on its own branch and lands on `main` quickly. The design branch then rebases on `main` and picks it up.

After this lands, *anyone* (you, the user, the design chat) can run `python manage.py seed_demo` to populate a local DB for demos, screenshots, eyeballing, validation.

## Scope

Build a **`seed_demo`** Django management command that fills a local dev DB with realistic data exercising every feature currently shipped:

- Multiple accounts of every supported type
- 8-12 months of varied transactions including all sign and category mixes
- Goals with mixed basket allocations summing to 100%
- The `is_savings_transfer` flag exercised so transfers don't pollute summaries

Out of scope for this branch:
- ❌ Production fixtures (this is dev-only).
- ❌ Plaid sandbox integration — `plaid_pull` already exists for that.
- ❌ Anything that touches the schema. **No model changes on this branch.**

## Where it lives

`accounts/management/commands/seed_demo.py`. Reasoning:
- The command is account-centric (accounts → transactions → goals).
- Avoids creating a new app just to host one command.
- `accounts/management/commands/` doesn't exist yet — create the directories with empty `__init__.py` files.

## CLI

```
python manage.py seed_demo [--username USERNAME] [--reset] [--months N]
```

Flags:
- `--username` — demo user to create or reuse (default: `demo`).
- `--reset` — delete all data owned by this user (accounts, transactions, goals, but not the User row itself), then re-seed. Without `--reset`, command is **idempotent**: re-running just re-asserts the seeded state without duplicating rows.
- `--months` — how many months of transaction history to generate (default: 12).

Exit cleanly with a summary line: `Seeded N accounts, M transactions, K goals for user <username>.`

## Idempotence

Re-running the command without `--reset` must NOT create duplicates.

Two ways to achieve this; pick one and stay consistent:

1. **Tag fixture rows.** Add a marker (e.g. `external_id="demo:<stable-key>"`) and use `update_or_create` keyed on it. The schema already has `external_id` on Account and Transaction (used by Plaid) — repurposing it for fixture keys is fine since real Plaid IDs never collide with `demo:*`.

2. **Existence check + skip.** Before generating, check if the demo user already has data; if so, no-op (and print a hint suggesting `--reset`). Simpler but less useful — partial seeds can't be filled in.

**Recommendation:** option 1 (`external_id` keyed). More predictable, plays well with `--reset`, and matches the Plaid pattern already in the codebase.

## What to generate

### User
- Reuse if `username` exists, else create with an unusable password (admin sets one if they want to log in).
- The post_save signal in `auth_app` auto-creates a Personal Space — don't create it manually.

### Accounts (4 total)
| Name | Type | Institution | Starting balance |
|---|---|---|---|
| Everyday Checking | checking | Chase | $2,400 |
| Emergency Fund | savings | Ally | $8,500 |
| Sapphire Visa | credit | Chase | $1,250 (positive = owed) |
| Costco Anywhere | credit | Citi | $340 |

Opt all four into the user's Personal Space (`space.accounts.add(...)`). Phase 1 auto-opt is currently per-account-creation; in this management command, do it explicitly to be safe.

### Transactions (~12 months, ~200-300 rows)

Generate from `today − months` to `today`. Use realistic merchants and amounts. Cover every shape the aggregations care about:

**Recurring monthly (income):**
- Paycheck, $3,400, 1st and 15th of each month → Checking.

**Recurring monthly (spending):**
- Rent, -$1,400, 1st of each month → Checking.
- Utilities (Comcast / PG&E / water), -$60 to -$180, mid-month → Checking.
- Streaming subs (Netflix, Spotify), -$10 to -$18 → mostly Sapphire Visa.

**Variable spending (random within realistic ranges):**
- Groceries (Trader Joe's, Whole Foods, Safeway), -$40 to -$140, ~6/mo → split between Checking and Sapphire.
- Dining (varied restaurant names), -$15 to -$80, ~10/mo → mostly Sapphire.
- Gas (Shell, Chevron), -$30 to -$60, ~2/mo → Sapphire.
- Costco runs, -$80 to -$220, ~1/mo → Costco Anywhere.

**Transfers (`is_savings_transfer=True`):**
- Monthly: $400 from Checking → Emergency Fund (saver's reflex).
- Monthly: variable card payments ($200–$800) from Checking → both credit cards (knock down the cards).

**Occasional:**
- Refund, +$60, twice in the year → Sapphire (refund convention is currently `amount > 0` on a spending category — see CLAUDE.md "Not yet decided"). One in the past 30 days so the design pass sees the edge case.
- Bonus paycheck, +$1,200, around month 6 → Checking.

Sign convention reminder (CLAUDE.md): positive = income (or debt-reduction on a credit account), negative = spending (or debt-incurred on a credit account).

### Goals (4)

| Name | Category | Target | Target date | basket_percent |
|---|---|---|---|---|
| 6-month Emergency Fund | emergency | $15,000 | None | 40 |
| Hawaii Trip | vacation | $4,000 | ~9 months from today | 25 |
| New Bike | recreation | $1,800 | None | 15 |
| Brokerage Top-up | investing | $6,000 | None | 20 |

Sum: 100. The goals view checks for `basket_balanced=True` so this is critical.

## Tests

Add `accounts/tests_seed_demo.py` (or extend an existing test file):

- Running `seed_demo` creates the expected counts (4 accounts, ≥150 transactions, 4 goals).
- Running it twice without `--reset` doesn't change counts (idempotence).
- Running with `--reset` cleans the user's data and re-seeds to the same counts.
- The Personal Space contains all 4 accounts.
- `sum(goal.basket_percent) == 100`.
- A spot-check of the transfer pair: at least one Checking → Sapphire pair, both `is_savings_transfer=True`, equal absolute amount.
- After seeding, `period_savings` returns a positive Decimal (sanity).

## CLAUDE.md update before merge

Add a short row / decision capturing this:

> **`dev-fixtures` — `python manage.py seed_demo`** for local dev data. Generates a demo user with 4 accounts (checking, savings, 2 credit), ~12 months of varied transactions including transfer pairs, and 4 balanced goals. Idempotent via `external_id="demo:*"` keys. `--reset` to wipe and re-seed. Not run in production; intended for design + screenshot + eyeballing workflows.

Goes in the **Decisions** section. No subsystem table row needed (it's a tool, not a subsystem).

## Things to be careful about

- **Don't run in production.** Add a check that fails loud if `DEBUG=False`, or at minimum print a warning. Easy to forget and seed prod by accident.
- **Don't create a User without a Space.** The post_save signal handles it; just don't bypass `User.objects.create_user`.
- **Don't import Plaid sandbox data here.** That's `plaid_pull`'s job. Keep `seed_demo` deterministic and offline — no API calls.
- **Random ≠ random.** Use a seeded RNG (`random.Random(seed=42)` or similar) so the same `seed_demo` invocation produces the same data each time. Makes screenshot diffs and "did the design change something?" reviews tractable.

## When done, before merging

1. Run `python manage.py test` — must pass.
2. Run `python manage.py seed_demo` on a clean DB — verify it succeeds.
3. Run again — verify it's idempotent (no duplicates, no errors).
4. Run with `--reset` — verify data is replaced cleanly.
5. Eyeball the home page after seed — should look populated, not empty.
6. Update CLAUDE.md per above.
7. Rebase on `main` if anything's landed there.
8. `git checkout main && git merge --no-ff dev-fixtures && git push origin main`.

After merge, the `ux-redesign` chat can rebase its branch on `main` and start using the command.
