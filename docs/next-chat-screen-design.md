# Next chat: screen design

Handoff brief for the **next Claude chat**, whose job is to design the screens (UI/UX layout) for the savings dashboard before any templates are written.

## Before starting the chat

1. Create and check out the branch:
   ```bash
   git checkout -b dashboard
   ```
2. Start the chat in this working directory.
3. First message to Claude: ask it to read `CLAUDE.md` and this file.

## Where we are now

- Django 4.2 scaffold runs; `python manage.py check` passes.
- Project folder renamed `dashboard/` → `config/` so the `dashboard` app name is free.
- `savings/` app exists as an empty placeholder — no models, views, or templates yet.
- Only URL wired up: `/admin/`.
- Database: SQLite, essentially empty.
- **No UI exists yet.** This chat's job is to decide what screens should exist and what goes on each one.

## Decisions already made

- Stack: Django templates + Chart.js (no SPA, no React).
- Single-user for now.
- Plaid is planned but **not** in scope for this chat. Screens should assume data will eventually be populated from Plaid + manual entry, but the design shouldn't depend on Plaid being done first.
- Freshness expectation: same-day/next-day via Plaid webhooks (not true real-time). Show a "last synced at …" indicator.

## Goal of the screen-design chat

Produce a concrete screen inventory and wireframe-level layout, written down in the repo. **No code yet.** Deliverables:

1. `docs/screens.md` — list of screens with URL, purpose, and primary elements on each.
2. `docs/wireframes/` — ASCII or markdown-table wireframes for each screen (no image tools needed).
3. Short list of reusable components (navbar, account card, transaction row, progress bar, etc.).
4. A rough visual hierarchy decision: what goes above the fold on the home dashboard.

## Screens likely needed (starting list — refine in chat)

- **Login / register** — from Django auth, minimal styling.
- **Home dashboard** — total savings, balance over time chart, recent transactions, goal progress.
- **Accounts list** — all linked accounts with current balance and last-sync time.
- **Account detail** — one account's transaction history and balance trend.
- **Transactions list** — filterable/searchable full history.
- **Goals list / goal detail** — progress bars, target date, linked account(s).
- **Settings** — Plaid link/unlink, manual account entry, CSV import entry point.

## Constraints to keep in mind

- Must be usable on a phone browser (not a native app). Mobile-first layout.
- Read-heavy: dashboard is for glancing at state, not data entry. Data entry lives in `/admin/` or dedicated forms.
- Keep the number of distinct screens small — this is a personal tool, not a product.

## Out of scope for the screen-design chat

- Writing HTML/CSS/templates.
- Picking a CSS framework (defer until wireframes are settled; likely Tailwind or plain CSS).
- Plaid integration.
- Auth flow implementation.

## When the chat is done

- Commit `docs/screens.md` + `docs/wireframes/` on the `dashboard` branch.
- Do **not** merge to `main` yet — a follow-up chat will implement the templates from these wireframes.
