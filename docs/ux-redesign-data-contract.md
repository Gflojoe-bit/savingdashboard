# `ux-redesign` data contract

Per-screen reference: what's already in the view context, what's missing, what to add as part of the redesign branch.

Read alongside `docs/ux-redesign-handoff.md`. The handoff is the **sequenced plan**; this is the **reference table** the design pass should check whenever a template needs data.

All views are `@login_required`; current Space scoping happens via `auth_app.models.current_space(user)` and `space.transactions_qs()`.

---

## Home — `templates/dashboard/home.html`
View: `dashboard/views.home` → `dashboard/views.py:183`

### Already in context
| Var | Type / shape | Source |
|---|---|---|
| `active_tab` | `'home'` | literal |
| `space` | `Space` instance (or `None`) | `current_space(user)` |
| `month_summary` | `{label, income, spending, savings, has_delta, income_delta, spending_delta, savings_delta, income_delta_display, spending_delta_display, savings_delta_display}` | `_month_summary(base_qs)` — calendar MTD + MTD-vs-prior-MTD delta |
| `charged_to_cards` | `{label, value, has_delta, delta, delta_display}` | `_charged_to_cards(base_qs)` — credit-card MTD spending disaggregation |
| `savings_goal_periods` | `[{key, label, saved, target, saved_display, target_display, pct}]` for week / month / three_months | `_savings_goal_periods(base_qs, user)` |
| `savings_series` | `{labels: [iso dates], values: [floats]}` | `_savings_over_time(base_qs)` — all-time cumulative |
| `goal_rows` | `[{goal: Goal, saved: Decimal}]` | per-goal basket-allocated saved amount |
| `recent_transactions` | `Transaction[]` (top 3, `.select_related("account")`) | `base_qs[:3]` |
| `accounts` | `Account` queryset | `space.accounts.all()` |

### Need to add for the new IA
| Var | Type | Why |
|---|---|---|
| `net_worth` | `Decimal` | Top banner: `assets − debt` |
| `assets_total` | `Decimal` | Sum of `current_balance` over savings-asset accounts. For the **Savings** row in the new split. |
| `debt_total` | `Decimal` | Sum of `current_balance` over credit accounts. For the **Debt** row. |
| `accounts_grouped` | `{savings: [Account], debt: [Account]}` | Optional convenience — design call whether to pre-group in Python or in the template. |

These come from the new `net_worth(user)` helper + `AccountQuerySet.savings_assets()` / `.debt()`. Backend prep commit #1.

### Notes for design
- **Delta display strings** use unicode minus (`−`), not ASCII hyphen — consistent with existing convention.
- **`charged_to_cards.value` is a positive Decimal** — already sign-flipped for display. *Disaggregation* of spending, not an additional subtraction. Don't double-count it.
- **`savings_series` can be empty** (`{labels: [], values: []}`) when the user has zero operational transactions. Template should handle.
- **`recent_transactions` is a queryset, not a list** — call `.count()` carefully (extra DB query). Iterate and let Django render.

---

## Accounts list — `templates/dashboard/accounts.html`
View: `dashboard/views.accounts` → `dashboard/views.py:215`

### Already in context
| Var | Type / shape |
|---|---|
| `active_tab` | `'accounts'` |
| `space` | `Space` instance (or `None`) |
| `accounts` | `Account` queryset (Space-scoped) |

### Need to add
| Var | Type | Why |
|---|---|---|
| `net_worth` | `Decimal` | Same banner as home |
| `assets_total` | `Decimal` | Group header for savings group |
| `debt_total` | `Decimal` | Group header for debt group |
| `accounts_grouped` | `{savings: [Account], debt: [Account]}` | Account list grouped by type |

### Notes for design
- **Account display:** `account.name`, `account.institution` (may be blank), `account.type` (one of `checking`, `savings`, `credit`), `account.current_balance` (computed property). `external_id` set means Plaid-linked.
- **Credit accounts:** `current_balance > 0` means "you owe this." Frame accordingly.

---

## Account detail — `templates/dashboard/account_detail.html`
View: `dashboard/views.account_detail(account_id)` → `dashboard/views.py:227`

### Already in context
| Var | Type / shape |
|---|---|
| `active_tab` | `'accounts'` |
| `account` | `Account` (scoped by `owner=request.user`) |
| `transactions` | `Transaction` queryset for that account, all-time |

### Already-derivable on `account`
- `account.current_balance` (property)
- `account.balance` (starting snapshot, rarely shown)
- `account.transactions.count()` etc.

### Need to add (design-dependent)
- If a "this month / 3 months" filter is added to the detail page, surface a similar `_month_summary`-shaped object scoped to the single account.
- Credit-specific UX (statement balance, due date, payment button) is **out of scope for this branch** — those need Bill model from `bill-tracker`.

---

## Transactions list — `templates/transactions/list.html`
View: `transactions/views.list_view` → `transactions/views.py:14`

### Already in context
| Var | Type / shape |
|---|---|
| `active_tab` | `'transactions'` |
| `months` | `[{label: 'Month YYYY', transactions: [Transaction]}]` — grouped by month |
| `active_type` | `''` or `'credit'` (filter chip state) |

### Notes for design
- Grouping is by `txn.date.replace(day=1)` then `groupby` — already sorted descending by date assumed (`space.transactions_qs()` orders by `-date, -created_at`).
- Each `Transaction` has: `account` (joined via `select_related`), `date`, `amount` (signed Decimal), `description`, `category`, `is_savings_transfer` (bool), `external_id` (if Plaid-imported).
- Filter chip already implemented: `?type=credit` narrows to `account.type=credit`. Add more chips as needed.

### Possible additions (design call)
- `?from=YYYY-MM-DD&to=YYYY-MM-DD` date range — small backend addition.
- `?q=text` description search — small backend addition.
- `?category=foo` category filter — Plaid populates `category` already; just needs filter logic.
- Any of the above don't have to land — flag in CLAUDE.md "Not yet decided" if not used.

---

## Transactions new — `templates/transactions/new.html`
View: `transactions/views.new` → `transactions/views.py:39`

### Already in context
| Var | Type / shape |
|---|---|
| `active_tab` | `'transactions'` |
| `form` | `TransactionForm` bound to `user` |

Standard Django form; design just needs to render fields and validation errors.

---

## Goals list — `templates/goals/list.html`
View: `goals/views.list_view` → `goals/views.py:34`

### Already in context
| Var | Type / shape |
|---|---|
| `active_tab` | `'goals'` |
| `rows` | `[{goal: Goal, saved: Decimal, pct: int, remaining: Decimal}]` |
| `savings` | `Decimal` — total `net_savings` (floored at 0) |
| `basket_total` | `Decimal` — sum of all `basket_percent` (should be 100) |
| `basket_balanced` | `bool` — `basket_total == 100` |

### Notes for design
- **`basket_balanced=False`** is the warning state — basket doesn't sum to 100. Design needs to surface this prominently (current placeholder says "rebalance via /goals/basket/").
- Each `Goal` has: `name`, `category` (string), `target_amount`, `target_date` (optional), `basket_percent`.
- `pct` is a clamped int 0–100; `remaining` is a Decimal already floored at 0.

---

## Goal detail — `templates/goals/detail.html`
View: `goals/views.detail(goal_id)` → `goals/views.py:48`

### Already in context
| Var | Type / shape |
|---|---|
| `active_tab` | `'goals'` |
| `goal` | `Goal` (scoped by `owner=request.user`) |
| `saved` | `Decimal` — saved amount per all-time net savings |
| `pct` | `int` (0–100, clamped) |
| `remaining` | `Decimal` (floored at 0) |
| `period_rows` | `[{key, label, saved}]` for past week / month / 3 months |

### Notes
- **No projection / completion-date math** — that's Phase 2 AI layer, gated on 2-3mo of real data. Don't try to surface it.

---

## Goal new — `templates/goals/new.html`
View: `goals/views.new` → `goals/views.py:71`

### Already in context
| Var | Type / shape |
|---|---|
| `active_tab` | `'goals'` |
| `form` | `GoalForm` bound to `user` |
| `existing_pct` | `Decimal` — sum of basket_percent across user's existing goals |
| `available_pct` | `Decimal` — `100 − existing_pct` |

### Notes
- Show `available_pct` prominently — it's the cap on the new goal's `basket_percent`. Form validates that the new total stays ≤ 100.

---

## Goal basket — `templates/goals/basket.html`
View: `goals/views.basket` → `goals/views.py:98`

### Already in context
| Var | Type / shape |
|---|---|
| `active_tab` | `'goals'` |
| `formset` | `BasketFormSet` over the user's goals |

### Notes
- Django messages framework is used for validation feedback — render `{% if messages %}` block.
- Server validates `sum(basket_percent) == 100` before save.

---

## Settings — `templates/dashboard/settings.html`
View: `dashboard/views.settings_view` → `dashboard/views.py:239`

### Already in context
| Var | Type / shape |
|---|---|
| `active_tab` | `None` |

Currently nearly empty. Design call: what should settings show?

### Likely additions (design-driven)
- `request.user` (name, email — already accessible via `{{ request.user }}`)
- Logout link (already in nav)
- Plaid-linked accounts list — out of scope here, comes with Plaid v2.
- Space membership info — out of scope, comes with Spaces Phase 2.
- Theme toggle (if dark mode is part of the design tokens) — pipe a setting from User profile.

If settings stays sparse for this redesign, that's fine — make it look intentional rather than empty.

---

## Login — `templates/auth_app/login.html`
View: Django's standard `LoginView` (in `auth_app/`)

### Context
Standard Django auth login: `form` (username/password), `next` (redirect target).

### Notes
- **Signup is invite-only.** No public registration form. Design should not include a "Sign up" link.
- Per `auth-handoff.md`, admin creates users via `/admin/` until Phase 2 invite flow lands.

---

## Base / chrome — `templates/base.html`

### Available everywhere via `request`
- `{{ request.user }}` — username, email (`request.user.is_authenticated` always True post-login_required)
- `{% url 'auth_app:logout' %}` for logout
- `{% url 'auth_app:login' %}` for the login redirect
- `active_tab` — view-passed string for nav highlighting (`'home'`, `'accounts'`, `'transactions'`, `'goals'`, or `None`)

### Out of scope for chrome (deferred branches)
- ❌ Space switcher in header — Spaces Phase 2.
- ❌ Notification bell / activity feed — no such system yet.
- ❌ Search bar in chrome — no global search backend.

---

## Models reference (read-only — don't change schemas in this branch)

For any template that needs model fields directly:

### `Account`
`owner` (User FK) · `name` · `type` (`checking` / `savings` / `credit`) · `institution` · `balance` (starting snapshot Decimal) · `external_id` (Plaid id, may be blank) · **`current_balance`** (property: `balance + sum(transactions.amount)`, quantized to cents).

### `Transaction`
`account` (FK) · `date` · `amount` (signed Decimal — positive=income, negative=spending) · `description` · `category` (string from Plaid) · `is_savings_transfer` (bool) · `external_id` · `created_at`.

### `Goal`
`owner` (User FK) · `name` · `category` (string) · `target_amount` · `target_date` (optional) · `basket_percent` (Decimal 0–100). Methods: `saved_amount(savings)`, `progress_pct(savings)`.

### `Space` / `SpaceMembership`
`Space.accounts` is the M2M through which Space members opt in accounts. `space.transactions_qs()` is the base queryset all aggregation helpers take.

---

## Things explicitly NOT in any context — don't try to render them

These are deferred or unimplemented; if the design needs them, it's an out-of-scope creep:

- ❌ Bill / due date / statement balance / overdue status — `bill-tracker` branch.
- ❌ Plaid Item list / institution sync status — Plaid v2.
- ❌ Multi-Space switcher / per-Space dashboards — Spaces Phase 2.
- ❌ Per-goal completion-date projections / suggested basket rebalances — AI Phase 2.
- ❌ Recurring transaction detection / scheduled transactions — not implemented.
- ❌ Tags / notes on transactions beyond `description` — not in the model.
- ❌ Multi-currency — not in scope.
