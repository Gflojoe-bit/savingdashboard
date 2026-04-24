# `chart` branch — handoff

Written for the next chat (on `main` or the next subsystem branch) picking up
after the savings-over-time chart lands.

## TL;DR

Fills the `.chart-placeholder` slot on the home page with a real cumulative
net-savings line chart. Chart.js 4 from CDN; data computed on the fly from
`Transaction.objects.operational()` (transfers excluded). One range
control — **1W / 1M / 3M / 1Y / All**, default 3M — slices the tail of a
single full-history series, so the y-axis stays anchored to actual cumulative
totals across zoom levels instead of re-baselining per window.

## Run it

```bash
git checkout chart    # or whichever branch name merged
source .venv/bin/activate
python manage.py runserver
# open http://127.0.0.1:8000
```

The chart sits between "Recent transactions" and "Goals" on the home page.
With an empty database it shows "No transactions yet." in place of the canvas.

## What's in the branch

- **`dashboard.views._savings_over_time(today=None)`** — builds a daily
  cumulative series from the earliest operational transaction through today.
  Returns `{"labels": [ISO date, …], "values": [float, …]}`. Transfers are
  excluded via `.operational()`; dips (net-negative days) are preserved
  (flooring is a goals-side policy, not a chart one). `home()` passes the
  dict in as `savings_series`.
- **`templates/dashboard/home.html`** — `.chart-placeholder` replaced with a
  `.chart-tile` containing range buttons, a `<canvas id="savings-chart">`,
  and a `.chart-empty` fallback. `{{ savings_series|json_script:"savings-series" }}`
  hands the full series to the client; an inline script pulls in Chart.js
  from `cdn.jsdelivr.net/npm/chart.js@4.4.1` and wires the range buttons to
  `Array.prototype.slice` the tail of the full series on click.
- **`static/css/app.css`** — the dashed `.chart-placeholder` block is gone.
  New `.chart-tile` / `.chart-range` / `.chart-canvas-wrap` / `.chart-empty`
  rules give the chart a bordered tile, 180px canvas height (160px under
  400px viewport), and reuse the existing `.period-btn` style for the range
  buttons so 1W / 1M / 3M on the goal tile and 1W / 1M / 3M / 1Y / All on
  the chart look consistent.

## Decisions this branch made

1. **Chart = absolute cumulative, not windowed cumulative.** One running
   total per day from day 1 forward. Range buttons zoom the visible
   X-window; the Y values are the true cumulative totals, so zooming in
   shows a near-flat slice of a big number rather than re-baselining to 0.
   The rolling goal tile already answers "am I saving at my usual rate
   right now" — the chart answers "how much, trending" instead.
2. **Chart range extends to 1Y + All, the goal tile stays 1W / 1M / 3M.**
   Calendar-to-date semantics conflict with rolling-past-N-days (that's
   why the tile dropped "year" in `rolling-periods`), but the chart is
   absolute cumulative with the buttons as a pure zoom — so wider
   ranges cause no tension. 3M is the default because it matches the
   tile default.
3. **Transfers excluded via `.operational()`, dips preserved.** Follows
   the aggregation-manager convention from `transfer-flag`. The chart
   does NOT floor at 0 — that floor is a goals allocation rule, and the
   chart's job is to tell the truth about the running savings balance.
4. **Chart.js from CDN, not vendored.** Single script tag, deferred until
   the chart exists. If offline dev ever matters, vendoring is a 1-line
   switch (download to `static/js/chart.umd.min.js`, swap the `src`).
5. **Full series shipped to the client; range slicing is client-side.**
   Keeps the range buttons instant (no request per click) and keeps the
   view simple. Series is `labels.length` floats; for a year of daily
   transactions that's 365 numbers, trivially small.

## Smoke test

From the branch, verified in the Django shell:

```
paycheck   +1000 (checking, 2026-04-01)
groceries  -200  (checking, 2026-04-05)
transfer   -500  (checking, 2026-04-10, is_savings_transfer=True)

today = 2026-04-12
_savings_over_time() → 12-day span
  2026-04-01 = 1000  (paycheck posts)
  2026-04-02 = 1000
  2026-04-03 = 1000
  2026-04-04 = 1000
  2026-04-05 = 800   (groceries)
  2026-04-06 = 800
  2026-04-07 = 800
  2026-04-08 = 800
  2026-04-09 = 800
  2026-04-10 = 800   (transfer excluded — would be 300 without operational())
  2026-04-11 = 800
  2026-04-12 = 800
```

- Empty DB → `_savings_over_time()` returns `{"labels": [], "values": []}`;
  template hides the canvas and shows the empty-state copy.
- Home view renders 200 with `chart-range`, `savings-series`, `savings-chart`,
  `chart.umd.min.js`, and all five range labels present in the HTML.
- Chart rendered and interactive in a browser (manual eyeball).

## Open scope still standing

Unchanged by this branch:

- **Delta vs prior period** on the calendar summary tiles — cheap
  motivation boost scoped in `rolling-periods`, not built.
- **Sparklines in the rolling goal tile** — tiny 30-day mini-chart in the
  corner, to visualize consistency even when the number is stable.
  Separate concern from this chart.
- **Best-week / best-month markers** — loss-aversion motivation layer on
  the chart. Later.
- **AI projection layer.** The chart is retrospective only; forward
  projections remain a Phase 2 item gated on ~2-3mo of transaction history.
- **Credit-cards subsystem.** New, larger — wants its own chat.
- **Importer, auth, real design.** Same order as prior handoffs.

## Notes on the code

- `_savings_over_time()` runs one `values("date").annotate(total=Sum(...))`
  query (grouped by date), then folds in Python over the full date span.
  At daily granularity a year is 365 iterations — fine. If the series
  ever grows past a few thousand points, switch to emitting only
  transaction-days (Chart.js interpolates between points correctly for a
  cumulative line) rather than one point per calendar day.
- The chart uses Chart.js's default `category` scale for the x-axis
  with ISO date strings as labels. No time-scale adapter (no
  `chartjs-adapter-date-fns` dep) — client-side tail-slicing is index-
  based, so a time scale isn't needed. The x-axis ticks are hidden
  (`scales.x.display: false`) so the absence of formatted date labels
  isn't visible; the tooltip uses the raw ISO date, which is legible
  enough for now.
- Y-axis auto-fits to the visible slice — this is what makes 1W read as a
  meaningful zoom rather than a flat line glued to the top of the tile.
  It's Chart.js default behavior; don't set `scales.y.min` if you want
  that behavior preserved.
- The inline init script follows the same pattern as the goal-tile
  toggle script above it in `home.html` — no module bundling, no
  external JS file. Two concerns live in one template; acceptable for
  a dashboard-home-only feature. Split into `static/js/home.js` if a
  third inline block would appear.
- Default active range is hardcoded in two places: `active` class on the
  `data-days="90"` button, and `setRange('90')` in the init script.
  They must stay in sync, same pattern as the goal-tile's `month`
  default.
- No tests. Still a project-wide gap. High-value targets for this branch:
  `_savings_over_time()` boundaries (empty DB, single transaction,
  transfer exclusion), and the home view's template context keys.

## Suggested next steps

1. **Merge `chart` → `main`.** Small, verified end-to-end.
2. **Delta tiles** on the calendar summary row — quick motivation win,
   same dashboard area.
3. **Credit-cards subsystem** — new chat, larger scope.
4. **Importer / auth / real design** — same order as prior handoffs.
