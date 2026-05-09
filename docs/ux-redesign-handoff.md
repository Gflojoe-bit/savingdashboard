# `ux-redesign` handoff

**Branch:** `ux-redesign` (created from `main` at `d7e0d2a`)
**Status:** Not started — this doc is the planning artifact.
**Audience:** A future Claude session doing the design pass.

First step in that chat: read `CLAUDE.md`, then this doc.

## Scope: polish what exists

The current look is intentionally placeholder per CLAUDE.md. This is the **first real design pass**. Path 1 from the chat that opened the branch: don't add new product surfaces — make the surfaces we already have feel finished.

### In scope

- Home (`templates/dashboard/home.html`)
- Accounts list (`templates/dashboard/accounts.html`)
- Account detail (`templates/dashboard/account_detail.html`)
- Transactions list (`templates/transactions/list.html`)
- Goals list / detail / new / basket (`templates/goals/*.html`)
- Settings (`templates/dashboard/settings.html`)
- Login (`templates/auth_app/login.html`)
- Base / chrome / nav / header (`templates/base.html`)
- Single CSS file: `static/css/app.css`

### Out of scope — do not creep

- ❌ `bill-tracker` (Bill model, bills strip, payment form) → own subsystem branch.
- ❌ Net page types (insights, trends, projections) → let real use surface need.
- ❌ Multi-Space switcher UI → Spaces Phase 2 branch.
- ❌ Plaid Link UI → Plaid v2 branch.
- ❌ AI projection layer for goals → gated on 2-3mo of real data.
- ❌ Multi-currency / i18n.

## Backend prep (commit #1 on this branch)

Two helpers are explicitly deferred from the `credit-cards` Decisions bullet to "the UX redesign pass" — that's now. Land them as the first commit so the design has real numbers to render against.

1. **`AccountQuerySet.savings_assets()`** and **`.debt()`** filters on `accounts/models.py`:
   ```python
   class AccountQuerySet(models.QuerySet):
       def savings_assets(self):
           return self.filter(type__in=[Account.CHECKING, Account.SAVINGS])
       def debt(self):
           return self.filter(type=Account.CREDIT)
   ```

2. **`net_worth(user)`** helper (place in `accounts/models.py`):
   ```python
   def net_worth(user):
       accounts = Account.objects.filter(owner=user)
       assets = sum((a.current_balance for a in accounts.savings_assets()), Decimal(0))
       debt = sum((a.current_balance for a in accounts.debt()), Decimal(0))
       return assets - debt
   ```

3. **Tests:** `assets − debt` math; debt accounts are subtracted (not added); empty case returns 0.

## Seed data (commit #2)

Realistic seed data is critical — empty screens look wrong even when the design is right.

Add a `python manage.py seed_demo` management command that:

- Creates a demo user (or uses `--username` flag), with Personal Space auto-attached via the existing post_save signal.
- Creates 3-4 accounts: 1 checking, 1 high-yield savings, 1-2 credit cards (different institutions).
- Creates 8-12 months of varied transactions: paychecks, recurring bills (rent, utilities, subscriptions), groceries, dining, entertainment, transfers between owned accounts (`is_savings_transfer=True`), card-swipe spending, card payments.
- Creates 3-5 goals with mixed progress and `basket_percent` summing to 100.
- Idempotent (running twice doesn't duplicate; safe to re-run).
- Use realistic merchant names + amounts so screens don't look stock.

Reset between iterations with `manage.py flush`.

## IA changes

Per the credit-cards "shipped narrow" decision, the home tile structure shifts:

| Section | Before | After |
|---|---|---|
| Top banner | — | **Net Worth** (assets − debt) |
| Balance group | Generic account totals | Split rows: **Savings** (assets) / **Debt** |
| Calendar-month tiles | Income / Spending / Savings | Unchanged content; redesign visually |
| Goals tile | Rolling 1W / 1M / 3M | Unchanged content |
| Charged-to-cards | Data piped, not rendered | **Render** — tile or inline disaggregation under spending |
| Savings-over-time chart | Cumulative line | Unchanged data; redesign visually |

**Account list/detail also moves from `dashboard/` to `accounts/`** per CLAUDE.md ("subsystem views move to their owning app on next touch"). Natural to do here since this branch touches the templates anyway.

## Design tokens

CLAUDE.md flags **direction-aware delta coloring** (income up = green, spending up = red, savings up = green) as gated on "design tokens." That gate is now this branch.

Approach: introduce CSS custom properties for color / type / spacing early in the design work. Single `:root` block at the top of `app.css` is enough. Then:

- Wire the delta lines on summary tiles to the new color tokens.
- Same tokens apply to chart strokes, urgency states, focus rings, etc.

Reference: `design-review/00-design-tokens.html` is an existing exploration of token direction.

## Existing design artifacts to read first

- `design-review/00-design-tokens.html` — color / type / spacing exploration.
- `design-review/01-dashboard.html` — dashboard layout exploration.
- `design-review/02-component-states.html` — component state matrix.
- `docs/placeholder-screens/*.html` — earlier screen sketches (01-home, 02-accounts, 03-account-detail, 04-transactions, 05-goals, 06-goal-detail, 07-settings).
- `docs/design-feedback.md` — any prior feedback notes.
- `docs/next-chat-screen-design.md` — direction notes from a prior session.

These are exploration artifacts; not all will translate. Use them as input, not constraint.

## Constraints

- **Mobile-first.** No max-width cap currently. Adding one is allowed but should be flagged as a deliberate decision (currently in CLAUDE.md "Not yet decided" — resolve this branch).
- **Single CSS file** (`static/css/app.css`). Splitting is allowed if the design grows, but motivate it.
- **Chart.js** is already loaded via CDN for the savings-over-time chart. Stay on it for new charts.
- **No external CSS frameworks** (no Tailwind, no Bootstrap). Hand-rolled CSS is the established convention.
- **Stay on existing fonts** unless adding a font is part of the design decision; if a new font is added, self-host or document the CDN choice.

## Decisions to make and capture in CLAUDE.md when done

- Color palette + type scale (the design tokens themselves).
- Whether to add a desktop `max-width` cap (resolves a "Not yet decided" item).
- Where the `charged_to_cards` tile renders (separate tile, inline under spending, or in transactions list only).
- Hero size for Net Worth: subtle banner row vs. dominant header.
- Whether delta lines stay on summary tiles or move to the chart.
- Single muted vs. direction-aware delta coloring (resolves a "Not yet decided" item).

## Test the design

- `python manage.py test` — must pass after backend prep + any view changes.
- `python manage.py check` — must pass.
- Mobile width (375px) and desktop width (≥ 1280px) — eyeball every screen.
- All `@login_required` views still gate correctly.
- After running `seed_demo`, every screen should render without errors and look populated.

## When done, before merging to main

1. Update CLAUDE.md:
   - Resolve "max-width" / "delta coloring" / "designer engagement" items in **Not yet decided** as appropriate.
   - Add a **Decisions** bullet capturing design token choices and IA defaults.
   - Update the `dashboard` row in the Subsystems table if the redesign changes its scope.
2. Move account list/detail views/templates from `dashboard/` to `accounts/`. Update URL routes.
3. Run full test suite.
4. Rebase on `main` before merging.
5. `git checkout main && git merge --no-ff ux-redesign && git push origin main`.

## Followup branches this redesign unblocks

- `bill-tracker` — bills strip on home now has design language to live in.
- Direction-aware delta coloring is shipped as part of this branch (no separate follow-up needed).
- Spaces Phase 2 — Space switcher in the header chrome can land easily once the design system exists.
