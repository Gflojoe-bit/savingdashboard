"""Dashboard aggregation views.

Accounts/transactions/goals detail lives in their own apps. This layer composes
them for the home screen and the accounts landing pages.
"""

from collections import defaultdict
from datetime import date, timedelta
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

    return [row("week", "1W"), row("month", "1M"), row("three_months", "3M")]


def _savings_over_time(today=None):
    """All-time cumulative net savings, one point per day from the first
    operational transaction through today.

    Transfers are excluded via `.operational()` so the line tracks real
    savings, not money shuffled between owned accounts. Dips (net-negative
    days) are preserved — flooring at 0 is a goals-side policy, and the
    chart's job is to show the true running balance of savings.

    Returns {"labels": [ISO date, …], "values": [float, …]}. The client
    zooms by slicing the tail — the y-axis stays anchored to actual
    cumulative totals, not re-baselined per window.
    """
    today = today or date.today()
    qs = Transaction.objects.operational()
    first = qs.order_by("date").first()
    if first is None:
        return {"labels": [], "values": []}

    start = first.date
    daily = defaultdict(Decimal)
    for row in qs.values("date").annotate(total=Sum("amount")):
        daily[row["date"]] = row["total"] or Decimal(0)

    labels, values = [], []
    running = Decimal(0)
    span = (today - start).days + 1
    for i in range(span):
        d = start + timedelta(days=i)
        running += daily.get(d, Decimal(0))
        labels.append(d.isoformat())
        values.append(float(running))
    return {"labels": labels, "values": values}


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
        'savings_series': _savings_over_time(),
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
