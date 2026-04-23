# Design feedback — second pass (placeholder only)

**Important context:** the real UX/visual design will be done separately by a professional designer. This pass is a **placeholder** — just enough structure for the developer to build Django templates against so the app is functional. The placeholder will be replaced later, so please prioritize:

1. **Clear structure** over visual polish
2. **Semantic HTML** that's easy to restyle later
3. **Mobile-first responsive layout** (the app will be used on phones)
4. **Covering all the screens** so every page has something to render

Don't spend time on a design system, color palette, icon set, or component states file. Those will come from the real designer.

## What to keep from the first pass

- The overall information architecture of the home dashboard was sensible (summary → accounts → chart → list). Keep that kind of thinking.
- That's it. Everything else can be redone simply.

## Scope — match `CLAUDE.md`

The first pass designed features that aren't in the project plan. Please stick to what's actually scoped. Drop these:

- **Spending categories** (Housing / Food / Travel / etc.) — no `Category` model exists
- **Credit cards and investment accounts** — only checking + savings in scope
- **Income vs spending chart** — requires categorization we don't have
- **Savings rate %** — same reason
- **"Sync accounts" button and "last synced" timestamps** — Plaid is deferred

And add what was missing:

- **Goals** section (planned subsystem, was absent)

## Screens needed

One simple HTML file per screen. No shared design tokens file, no component states file. Inline or minimal CSS is fine — just make it readable. Mobile-first.

1. **`01-home.html`** — total savings (big number), a placeholder chart area (just an empty bordered box labeled "Savings over time"), list of goals with progress bars, list of recent transactions, list of accounts.
2. **`02-accounts.html`** — all accounts (name, type, balance).
3. **`03-account-detail.html`** — one account's name + balance at top, list of its transactions below.
4. **`04-transactions.html`** — full transaction list.
5. **`05-goals.html`** — all goals with progress bars.
6. **`06-goal-detail.html`** — one goal: name, target amount, current amount, progress bar, target date.
7. **`07-settings.html`** — basically empty. A link to `/admin/` and a "CSV import" link placeholder.

Login/register: skip — we'll use Django's default templates.

## Layout requirements

- **Mobile-first.** Design at 375px wide first. Single column, stacked. Touch targets at least 44×44px.
- **Desktop is optional** — if you want to add a `@media (min-width: 768px)` rule to widen things on larger screens, fine. Not required.
- **Plain semantic HTML.** Use `<nav>`, `<main>`, `<section>`, `<article>`, `<ul>`, `<table>` where appropriate. Real designer will restyle — clean markup makes that easier.
- **Minimal CSS.** Borders, padding, basic type hierarchy. No fancy fonts, no custom color palette, no icons. System font stack is fine. Grey and black is fine.

## Placeholder content

Use obviously-fake data so nobody mistakes it for real:

- Accounts: "Checking (Bank A)", "Savings (Bank B)"
- Goals: "Emergency Fund", "Vacation"
- Transactions: "Grocery store", "Paycheck", "Rent"

## Deliverable

Zip the 7 HTML files. No tokens file, no states file, no icon assets. Just the screens.
