# `goals` branch — handoff

Written for the next chat (on `main` or the next subsystem branch) picking up after goals lands.

## TL;DR

`goals` adds a real `Goal` model with a **basket-allocation** progress model: every dollar of net savings (income − spending, floored at 0) is split across goals by a per-goal `basket_percent`. The fake `GOALS` and `SAVINGS_GOAL_PERIODS` are gone, the home tile + goals list/detail pages now read real rows, and `dashboard/fake_data.py` is fully removed (it was the last fake-data consumer).

## Run it

```bash
git checkout goals
source .venv/bin/activate
python manage.py migrate
python manage.py runserver
```

Add goals at http://127.0.0.1:8000/goals/new/ (or via admin). The new-goal form requires `basket_percent` and rejects unless the total across all goals is exactly 100% — rebalance via http://127.0.0.1:8000/goals/basket/ first if there's no room.

## What's in the branch

- **New `goals/` app** with `Goal` model — fields: `name`, `category` (choices: emergency / investing / vacation / home / other), `target_amount` (≥ 0.01), `target_date` (nullable), `basket_percent` (0–100), `created_at`. Methods: `saved_amount(savings)`, `progress_pct(savings)`. Module-level helpers `net_savings(qs=None)` and `period_savings(today=None)`.
- **Migration** — `goals/migrations/0001_initial.py` creates `goals_goal`.
- **Admin** — `Goal` registered with list, filter (category), search (name).
- **Forms** — `GoalForm` exposes `basket_percent` and runs a `clean()` that validates the cross-goal total; `BasketFormSet` is a modelformset for editing all `basket_percent` values together.
- **Views + URLs** in `goals/` — `/goals/`, `/goals/<id>/`, `/goals/new/`, `/goals/basket/`. The dashboard's old `goals` and `goal_detail` views/URLs/templates are deleted; the bottom nav now points at `goals:list`.
- **Dashboard rewired** — `dashboard/views.py::home` now computes:
  - `goal_rows` — each goal with its lazy `saved_amount` against all-time net savings.
  - `savings_goal_periods` — W/M/Y net savings vs. **sum of all goal targets** (not per-goal). Reuses `goals.models.period_savings()`.
- **`dashboard/fake_data.py` deleted** — `GOALS` and `SAVINGS_GOAL_PERIODS` were the last consumers, and previous handoffs flagged the file for removal once goals landed.
- **CLAUDE.md** — Decisions section gets five new entries (basket model, lazy progress, aggregate W/M/Y, negative-savings clamp, basket-100% creation rule); the "Weekly/Monthly/Yearly savings target" item is removed from "Not yet decided"; "Not yet decided" gains entries for AI projections, savings-transfer flag, per-category contribution form, and goal edit/delete UI.

## Decisions this branch made

All in CLAUDE.md's **Decisions** section:

1. **Basket-allocation model.** Each goal has a `basket_percent`; net savings split across goals by weight. Basket must total 100% (form-level validation).
2. **Lazy progress, no allocation table.** Recomputed on every page load. Trade: changing the basket retroactively rewrites past progress. An `Allocation` snapshot table can land later if real history is needed.
3. **Home W/M/Y tile is aggregate, not per-goal.** Saved = net savings in period; target = sum of all goal targets.
4. **Net savings floored at 0.** Negative cash flow in a period contributes nothing — you can't distribute negative savings.
5. **Goal creation requires `basket_percent`.** Cross-goal total must be exactly 100% to save; the new-goal page shows an "X% allocated · Y% available" hint so the user knows whether to rebalance first.

## Review-pass fixes (after the initial build)

A code review surfaced several issues; all fixed in this branch:

- **Negative savings broke math** → clamped to 0 in `net_savings()` and the dashboard's period helper.
- **No per-field bounds on `basket_percent`** → `MinValueValidator(0)` + `MaxValueValidator(100)`.
- **`target_amount` could be 0** (causing `<progress max="0">`) → `MinValueValidator(0.01)`.
- **`progress_pct` truncated** (99.9% → 99%) → switched to `round()`.
- **Basket view used `zip(qs, formset.forms)`** — order coupling. Refactored to iterate `formset.forms` and read `form.instance.name`.
- **Three near-duplicate period helpers** (`_period_savings` in goals, `_savings_in` + `_savings_goal_periods` in dashboard) → collapsed into a single `goals.models.period_savings(today)` returning `{week, month, year, all}`.
- **`total_savings()` was actually net** (income − spending) → renamed `net_savings()`. Variable `savings_total` → `savings`.
- **List template mixed `floatformat:0` and `:2`** → reconciled to `:0` for compact list/tile views; detail page keeps `:2` for precision.

## Smoke tests run

- Two goals (`Emergency` $5,000 @70%, `Vacation` $2,000 @30%) + a $1,000 paycheck and $200 spend → list shows `Total saved: $800`, Vacation 12% complete, Emergency 11% complete (math: 800 × 0.70 / 5000 = 11.2%, rounds to 11; 800 × 0.30 / 2000 = 12%).
- Net negative period (income $500, spending $800) → `net_savings()` returns 0; all goal `saved_amount` returns 0. Add a $1,000 bonus and net flips to $700; goals immediately reflect.
- `GoalForm` with `basket_percent=30` while existing goals already total 100% → form rejects with `"Basket must total 100%. Existing goals use 100%, so this goal needs to be 0%."` After rebalancing first goal to 70%, second goal at 30% saves cleanly.
- Field validators reject `target_amount=0`, `basket_percent=-10`, `basket_percent=150` at the model level.
- All 6 routes (`/`, `/goals/`, `/goals/<id>/`, `/goals/new/`, `/goals/basket/`, plus admin) return 200; basket POST returns 302 redirect with persisted percentages.

## What's still on fake / placeholder

Nothing. Every screen now reads from real models. The `static/css/app.css` styles for goals (`.goal-list`, `.goal-row`, `.goal-meta`, etc.) carry over unchanged from the placeholder pass.

## Open scope decisions still standing

All recorded in CLAUDE.md's "Not yet decided":

- **"Savings over time" chart data source.** Unchanged by this branch.
- **AI projection layer (Phase 2).** Per-goal completion-date inference + basket-rebalance suggestions. Gated on ~2-3 months of transaction history.
- **`Transaction.is_savings_transfer` flag.** Transfers from checking → savings currently double-count: they look like spending in checking, which shrinks net savings, so basket math under-reports. Need a flag (or `category="transfer"`) so the income−spending math excludes them.
- **Per-category amount/date contribution form.** Two interpretations (recurring per-goal contribution vs. one-off manual allocations); pick one before building.
- **Goal edit + delete views.** Currently admin-only.
- **Where accounts list/detail lives long-term.** Still in `dashboard/`. Goals followed CLAUDE.md's suggestion and moved into its own app; accounts can do the same when next touched.

## Suggested next steps (priority order)

1. **Merge `goals` → `main`.** Verified end-to-end.
2. **`Transaction.is_savings_transfer` flag** — the most visible correctness gap. Probably belongs in the `transactions` chat as a small follow-up.
3. **Chart** — wire Chart.js into the `.chart-placeholder` on home. Now that there's full transaction + goals data, "savings over time" is computable on the fly.
4. **Importer** — CSV import of transactions; deferred since the start. Plaid backfill (3mo / 12mo / 24mo / "everything") to be decided in that chat.
5. **Auth** — Django built-ins, single → multi user.
6. **AI projection layer** for goals (Phase 2).

## Notes on the code

- `Goal.Meta.ordering = ["-created_at"]` — list view shows newest first.
- `BasketFormSet` is a `modelformset_factory(Goal, ...)` with `extra=0` so users edit existing goals only; goal creation is its own form. The basket template iterates `formset.forms` and reads `form.instance.name` directly (no parallel queryset to keep aligned).
- `goals.models.period_savings(today=None)` is the single source of truth for "net savings over week/month/year". Both goal detail and the dashboard W/M/Y tile call it.
- `GoalForm.clean()` queries `Goal.objects.exclude(pk=self.instance.pk)` so the 100% check works for both create (no pk yet) and edit (excludes self).
- No tests yet; still a project-wide gap. High-value targets: `Goal.saved_amount()` math, `GoalForm.clean()` 100% rule, `period_savings()` boundaries, dashboard `_savings_goal_periods()` shape.
- Basket validation is form-level only — admin still allows arbitrary individual percentages (per-field validators bound them to [0,100], but admin won't enforce the 100% sum). Acceptable for single-user dev; revisit when multi-user or auth lands.
