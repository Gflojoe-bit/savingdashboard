# `dashboard-ui` branch — handoff

Written for the next chat (likely on `main`) that decides what to merge and what to build next.

## TL;DR

`dashboard-ui` turns the empty Django scaffold into a **fully clickable, mobile-responsive placeholder app** for every screen in the project. No real data, no models — every view reads from a single `dashboard/fake_data.py`. Ready to merge into `main` as the new baseline.

## Run it

```bash
git checkout dashboard-ui
source .venv/bin/activate
python manage.py runserver
# open http://127.0.0.1:8000
```

Admin panel still lives at `/admin/`. Bottom tab nav is mobile-convention: Home / Accounts / Transactions / Goals. Settings is a top-right link on home.

## What's in the branch (4 commits ahead of `main`)

1. **Design feedback + placeholder HTML** — see `docs/design-feedback.md` and `docs/placeholder-screens/`. The placeholders were designed in a separate chat and explicitly scoped as *throwaway scaffolding*; real UX will come from a professional designer later.
2. **Django port** — created a `dashboard/` app, consolidated CSS into `static/css/app.css`, split templates into `templates/base.html` + `templates/dashboard/*.html`.
3. **Home dashboard rework + mobile responsive pass** — 2×2 tile grid (Income / Spending / Savings / Goal), goal tile with W/M/Y period toggle, accounts in a real `<table>` that collapses to stacked rows under 400px viewport. Every section tested down to 320px (original iPhone SE).
4. **Section reorder on home** — recent transactions moved up, before savings-over-time chart.

Git log for reference:

```
7be6b86 Reorder home sections: recent transactions before savings over time
a83c068 Rework home dashboard — 2x2 tile grid, goal tile, mobile responsive
b0f1724 Port placeholder screens to Django templates
668a1ab Add placeholder UI screens from designer
```

Plus one earlier commit already on `main`: `41db545 Add design feedback for placeholder mockup pass`.

## Screens delivered

| URL | Template | What's there |
|---|---|---|
| `/` | `dashboard/home.html` | 4 summary tiles, accounts table, recent transactions, chart placeholder, goals |
| `/accounts/` | `dashboard/accounts.html` | List of all accounts, tap for detail |
| `/accounts/<id>/` | `dashboard/account_detail.html` | One account's header + its transactions |
| `/transactions/` | `dashboard/transactions.html` | All transactions grouped by month |
| `/goals/` | `dashboard/goals.html` | List of goals with progress bars |
| `/goals/<id>/` | `dashboard/goal_detail.html` | One goal: saved / target / progress |
| `/settings/` | `dashboard/settings.html` | Links to admin + (stub) CSV import |

## The "fake data" swap points

All placeholder data lives in **`dashboard/fake_data.py`**. When a real subsystem branch lands, it should replace its slice with a real queryset. Rough mapping:

| fake_data name | Replace with (when subsystem is real) |
|---|---|
| `ACCOUNTS` | `Account.objects.all()` — from the `accounts` subsystem |
| `TRANSACTIONS_BY_ACCOUNT` | `account.transactions.order_by('-date')` |
| `TRANSACTIONS_BY_MONTH` | `Transaction.objects.all()` grouped by month |
| `RECENT_TRANSACTIONS` | `Transaction.objects.order_by('-date')[:3]` |
| `GOALS` | `Goal.objects.all()` — from the `goals` subsystem |
| `TOTAL_SAVINGS` | `sum(a.balance for a in savings accounts)` |
| `MONTH_SUMMARY` | computed: income = sum of credit transactions this month; spending = sum of debits; savings = delta |
| `SAVINGS_GOAL_PERIODS` | computed per period (week/month/year), probably against a user-configured weekly/monthly/yearly savings target |

The views in `dashboard/views.py` are all function-based, short, and pass data as template context. Each one has one or two `fake_data.X` references that are the cleanest upgrade points.

## Open scope decisions

Things the home dashboard currently *assumes* but which aren't scoped in `CLAUDE.md` yet:

1. **Income / Spending / Savings summary numbers** — need a way to split transactions into income vs spending. Simplest heuristic: positive amount = income, negative = spending. That works without a `Category` model. Flag for the `transactions` subsystem.
2. **Weekly / Monthly / Yearly savings goals** — the goal tile on home assumes the user has a target amount for each period. Not covered by the existing `goals` subsystem scope (which is about named savings goals like "Emergency Fund"). Either:
   - Extend `goals` to include a recurring target, OR
   - Add a "Savings plan" settings field (one week/month/year target across the whole app)
3. **"Savings over time" chart** — a dashed placeholder box currently. Needs a data source: probably a daily or weekly snapshot of total-savings-account balance. Requires either (a) a snapshot table written daily, or (b) computing from first-transaction-forward. Relevant when Chart.js gets wired up.

## Scope explicitly *not* attempted here

Per `docs/design-feedback.md`, the placeholder skipped:

- Spending categorization UI (no `Category` model planned)
- Credit and investment account types (scope is checking + savings)
- Plaid sync flow (deferred)
- Login / register screens (will use Django defaults)
- Real design / icon system (professional designer will redo)

Don't treat the current look as the target. It's intentionally minimal.

## Suggested next steps (in priority order)

1. **Merge `dashboard-ui` → `main`** — makes it the new baseline. Low risk; no model changes, nothing to migrate.
2. **Start `accounts` subsystem** — easiest first real-data step. Define `Account` model, swap `fake_data.ACCOUNTS` for `Account.objects.all()`, remove the fake entry. Views and templates don't need to change.
3. **Then `transactions`** — adds the `Transaction` model with FK to `Account`. Swaps `fake_data.TRANSACTIONS_*` and computes `MONTH_SUMMARY` + `RECENT_TRANSACTIONS` + `TOTAL_SAVINGS` from real data.
4. **Then `goals`** — replaces `fake_data.GOALS`. Also pick a home for the W/M/Y period target (see Open Scope #2 above).
5. **Chart** — wire Chart.js into the `.chart-placeholder` box. Can be done any time after #3 (needs transaction data to compute savings-over-time).
6. **Importer** — CSV import was deferred in the original scope; the Settings page has a placeholder link.
7. **Auth** — currently anonymous. Add login/register with Django's built-in views whenever multi-user becomes relevant.
8. **Real design** — hand it to a professional designer. The structure should survive; mostly `static/css/app.css` and minor template reshaping.

## Notes on the code

- CSS is one file (`static/css/app.css`), mobile-first, with breakpoints at **400px** and **340px**. Max-width is not capped, so on a desktop browser the page currently stretches full-width — there's no media query above 400px. Easy to add a cap like `max-width: 640px; margin: 0 auto` on `<main>` + `<header.page-header>` if the desktop-stretched look bothers anyone.
- The goal-tile W/M/Y toggle is the only JavaScript on the site (~15 lines inline at the bottom of `home.html`). It has no persistence — refreshing snaps back to "M". If you want the selection to survive reload, localStorage is 2 extra lines.
- `.gitignore` excludes the first-pass rejected design zip + folder (`design for saving app.zip`, `design-review/`) — they're still on disk locally but not tracked. Same for `.claude/settings.local.json`.
- The `savings/` app from the original scaffold is empty and untouched. Probably safe to delete in a small cleanup commit, or leave until someone finds an actual use for it.

## Known gaps

- **No tests.** Haven't written any. Low priority for a UI-only branch, but worth adding when subsystems get real models.
- **`ALLOWED_HOSTS` is empty** in `config/settings.py`. Works fine in dev (Django allows localhost/127.0.0.1 when DEBUG=True), but the Django test-client trick needs `HTTP_HOST='127.0.0.1'` passed explicitly.
- **No favicon.** Browser shows a 404 in the server log every page load. Purely cosmetic.

## Questions to decide before going further

- Should the dashboard views stay in `dashboard/` long-term, or migrate into the owning apps as they land? CLAUDE.md is ambiguous. A reasonable rule: keep the home page in `dashboard/` (it's aggregation), move accounts list/detail to `accounts/`, transactions list/detail to `transactions/`, goals to `goals/`.
- Desktop behaviour: cap the layout width or let it stretch?
- When to show the app to the professional designer — now (to start real design in parallel with subsystem work) or after real data is flowing?
