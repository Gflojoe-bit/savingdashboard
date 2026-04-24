"""Dashboard aggregation views.

Accounts/transactions/goals detail lives in their own apps. This layer composes
them for the home screen and the accounts landing pages.
"""

from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.shortcuts import get_object_or_404, render

from accounts.models import Account
from goals.models import Goal, period_savings
from transactions.models import Transaction


def _month_summary(today=None):
    """Income / spending / savings for the current calendar month.

    Delegates to Transaction.objects.in_range(...).summary() so the math
    definition lives in one place (transactions.models.TransactionQuerySet).
    """
    today = today or date.today()
    start = today.replace(day=1)
    return {
        "label": today.strftime("%B %Y"),
        **Transaction.objects.operational().in_range(start, today).summary(),
    }


def _savings_goal_periods(today=None):
    """W / M / Y net savings vs. sum of all goal targets."""
    periods = period_savings(today)
    target = Goal.objects.aggregate(s=Sum("target_amount"))["s"] or Decimal(0)

    def row(key, label):
        saved = periods[key]
        return {
            "key": key,
            "label": label,
            "saved": saved,
            "target": target,
            "saved_display": f"{saved:,.0f}",
            "target_display": f"{target:,.0f}",
            "pct": int((saved / target) * 100) if target > 0 else 0,
        }

    return [row("week", "Week"), row("month", "Month"), row("year", "Year")]


def home(request):
    recent = (
        Transaction.objects.select_related("account")
        .order_by("-date", "-created_at")[:3]
    )
    savings_total = Transaction.objects.aggregate(s=Sum("amount"))["s"] or Decimal(0)
    goals = Goal.objects.all()
    goal_rows = [
        {
            "goal": g,
            "saved": g.saved_amount(savings_total),
        }
        for g in goals
    ]
    return render(request, 'dashboard/home.html', {
        'active_tab': 'home',
        'month_summary': _month_summary(),
        'savings_goal_periods': _savings_goal_periods(),
        'goal_rows': goal_rows,
        'recent_transactions': recent,
        'accounts': Account.objects.all(),
    })


def accounts(request):
    return render(request, 'dashboard/accounts.html', {
        'active_tab': 'accounts',
        'accounts': Account.objects.all(),
    })


def account_detail(request, account_id):
    account = get_object_or_404(Account, pk=account_id)
    return render(request, 'dashboard/account_detail.html', {
        'active_tab': 'accounts',
        'account': account,
        'transactions': account.transactions.all(),
    })


def settings_view(request):
    return render(request, 'dashboard/settings.html', {
        'active_tab': None,
    })
