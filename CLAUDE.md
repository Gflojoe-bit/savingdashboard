# Savings Dashboard

A Django app to track savings — accounts, transactions, goals, and a dashboard with charts.

## Stack

- Python 3.9 + Django 4.2 LTS
- SQLite (dev)
- Django templates + Chart.js (planned) for the dashboard UI
- stdlib `venv` at `.venv/`

## Setup

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py runserver
```

## Workflow: one branch + one chat per subsystem

Each major subsystem lives on its own branch and is developed in its own Claude chat. This keeps conversations focused and avoids context churn. `main` is the integration branch — merge subsystem branches in when they're ready.

When starting a chat on a subsystem branch, the first thing to do is read this file and the subsystem's scope below.

## Subsystems (branches)

| Branch | Scope |
|---|---|
| `auth` | User accounts, login/logout, registration, password reset. Uses Django's built-in `auth` app. |
| `accounts` | Bank/savings account records — name, type, institution, current balance. Model + admin + basic CRUD views. |
| `transactions` | Deposits/withdrawals/transfers tied to an account. Model + list/create views. Source of truth for balances (derived via sum). |
| `goals` | Savings targets — name, target amount, target date, linked account(s). Progress calculation. |
| `dashboard` | Home view: totals, recent activity, progress charts (Chart.js). Read-only aggregation layer. |
| `import` | CSV import of transactions. Column mapping, deduplication, preview-before-commit. |

## Conventions

- Project folder (settings + root URLs) is `config/`. Apps live at the repo root alongside it.
- App per subsystem: `auth_app/`, `accounts/`, `transactions/`, `goals/`, `dashboard/`, `importer/` (Django reserves `auth` and `import`).
- Migrations are committed.
- Keep subsystem branches small and mergeable — rebase on `main` before merging.

## Not yet decided

- Deployment target (local-only for now).
- Multi-user vs single-user — start single-user, revisit.
- Whether to add Plaid or stay manual/CSV-only.
