# `rolling-periods` branch — handoff

Written for the next chat (on `main` or the chart chat) picking up after
rolling-periods lands.

## TL;DR

Replaces the goal-tile's week / month / year calendar-period-to-date
buttons with rolling **1W / 1M / 3M** windows ending today. Goal detail's
"recent savings allocated" section follows suit. Home summary tiles
(Income / Spending / Savings) still use calendar month — intentional,
see the retrospective-vs-motivation decision below. One commit ahead of
`main`.

## Run it

```bash
git checkout rolling-periods
source .venv/bin/activate
python manage.py runserver
```

The goal tile on `/` shows three buttons: **1W**, **1M**, **3M** (default
M). Clicking toggles between rolling 7 / 30 / 90-day totals.

## What's in the branch

```
9aa126e Switch goal period tiles to rolling 1W / 1M / 3M windows
```

- **`goals.models.period_savings()`** — keys change from `week / month /
  year / all` to `week / month / three_months / all`. Each key now maps
  to a rolling window ending today:
  - `week` = today − 6 → today (7 days)
  - `month` = today − 29 → today (30 days)
  - `three_months` = today − 89 → today (90 days)
  - `all` = unchanged
- **`dashboard.views._savings_goal_periods`** — rows now labeled
  `1W / 1M / 3M` for the tile buttons. Three rows, not four.
- **`goals.views.detail`** — period_rows labels change to `Past week /
  Past month / Past 3 months` for the "recent savings" section (reads
  better than "This past week" would have).
- **`templates/dashboard/home.html`** — goal-tile buttons drop the
  `|slice:":1"` filter. Short labels `1W / 1M / 3M` come straight from
  the view. Default active period stays `month`.
- **`templates/goals/detail.html`** — "This {{ label|lower }}" is now
  "{{ label }}" since labels are self-contained.

## The decision this branch locks in

**Savings is computed retrospectively, over a past window ending today.**
There is no forward projection in the base aggregation. Future-dated
transactions are not counted as savings until their date arrives. Any
forecast / projection feature is a separate layer (see the AI projection
item in `CLAUDE.md` "Not yet decided").

This is why `period_savings()` no longer exposes "year" — calendar-to-date
semantics (Jan 1 → today on Apr 24 = 114 days) are inconsistent with
"past 3 months". Rolling windows enforce retrospective thinking: every
window is "the past N days, ending now."

## Why not also change the home summary tiles

The top-row tiles (Income / Spending / Savings) still use calendar
month (`day=1` → today). This is deliberate — calendar and rolling
serve different UX jobs:

- **Rolling (goal tile)**: stable signal. If the user is saving
  routinely, the rolling number barely moves. A sudden drop is a real
  event worth noticing. Honest answer to "am I on pace?"
- **Calendar (summary tiles)**: resets on the 1st and grows through the
  month. Motivating — the user *sees* progress accumulate. Partly
  theater (on the 30th the number is big because the window is big),
  but the feedback loop drives engagement.

Both patterns are correct for their respective roles. Do not
"normalize" them without a UX conversation first.

## Smoke test

Four transactions placed at the window boundaries:

```
-3 days:    +$100   →  counts in 1W, 1M, 3M, all
-20 days:   +$200   →  counts in 1M, 3M, all
-60 days:   +$400   →  counts in 3M, all
-200 days:  +$800   →  counts in all only

period_savings() returned:
  week         = 100
  month        = 300
  three_months = 700
  all          = 1500
```

Exact boundary math confirmed.

## Open scope still standing

Unchanged by this branch:

- **Savings over time chart** — the `.chart-placeholder` on home is
  still unfilled. The retrospective windows built here are a natural
  data source (a 90-day line chart of cumulative savings).
- **Delta vs prior period** on the calendar summary tiles — a small
  motivation boost ("$890 this month, +$140 vs last month"). Not
  built; scoped in the rolling-periods chat.
- **Sparklines in the rolling tile** — tiny 30-day mini-chart in the
  goal tile corner. Visualizes consistency even when the number is
  stable.
- **Best-week / best-month markers** — loss-aversion motivation. Later.

## Notes on the code

- No schema changes. No migrations. Pure view + template + helper rewiring.
- `period_savings()` still returns an `all` key — goal detail uses it
  for the main progress bar. Not exposed in the tile toggle.
- The `month` key on the goal tile is now a *30-day rolling* window,
  while the `month_summary` dict on the same page is a *calendar-month*
  window. Same word, different meaning. If that ambiguity ever bites,
  rename the tile key (e.g. `rolling_30`) rather than collapse the
  two concepts.
- Default active period in the tile is hardcoded to `month` in two
  places: `data-active-period="month"` on the `.goal-tile` div, and
  `{% if period.key == 'month' %}active{% endif %}` in the button loop.
  They must stay in sync.
- No tests. Still a project-wide gap. High-value targets:
  `period_savings()` boundaries (the smoke test covers them; a unit
  test would pin them).
- Smoke-testing this branch wiped the local dev DB. `db.sqlite3` isn't
  tracked; re-seed via admin on next runserver.

## Suggested next steps

1. **Merge `rolling-periods` → `main`.** Small, verified.
2. **Chart on home** — `docs/dashboard-ui-handoff.md` has this as open
  scope; now that retrospective windows exist, a 90-day rolling chart
  of cumulative net savings is the obvious shape.
3. **Delta tiles** — quick win for motivation on the calendar summary
  row.
4. **Credit-cards subsystem** (new — see CLAUDE.md). Larger, needs its
  own chat.
