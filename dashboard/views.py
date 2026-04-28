"""Dashboard aggregation views.

Accounts/transactions/goals detail lives in their own apps. This layer composes
them for the home screen and the accounts landing pages.
"""

import calendar
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render

from accounts.models import Account
from auth_app.models import current_space
from goals.models import Goal, period_savings
from transactions.models import Transaction


def _format_delta(value):
    """Format a Decimal as '+$140.00' or '−$50.00' for display.

    Uses an actual unicode minus sign (−) to match the existing template
    convention on the savings tile.
    """
    if value < 0:
        return f"−${abs(value):,.2f}"
    return f"+${value:,.2f}"


def _prior_month_range(today):
    """Return (start, end) for the same-day-of-month window in the prior month.

    On today=Apr 24, returns (Mar 1, Mar 24). On Mar 31, when Feb only has
    28 days, caps end to Feb 28 so we never construct an invalid date.
    """
    if today.month == 1:
        year, month = today.year - 1, 12
    else:
        year, month = today.year, today.month - 1
    last_day = calendar.monthrange(year, month)[1]
    end_day = min(today.day, last_day)
    return date(year, month, 1), date(year, month, end_day)


def _month_summary(base_qs, today=None):
    """Income / spending / savings for the current calendar month, plus
    month-over-month deltas comparing MTD to the same-day-of-month window
    in the prior month.

    Delegates to base_qs.in_range(...).summary() so the math definition
    lives in one place (transactions.models.TransactionQuerySet). `base_qs`
    is the Space-scoped Transaction queryset.

    Delta fields are only populated when the prior-month window contains
    at least one operational transaction — first-month users and empty
    gaps don't get misleading "+$X vs $0" lines.
    """
    today = today or date.today()
    start = today.replace(day=1)
    current = base_qs.operational().in_range(start, today).summary()

    prev_start, prev_end = _prior_month_range(today)
    prev_qs = base_qs.operational().in_range(prev_start, prev_end)

    result = {
        "label": today.strftime("%B %Y"),
        "has_delta": False,
        **current,
    }

    if prev_qs.exists():
        prev = prev_qs.summary()
        result["has_delta"] = True
        result["income_delta"] = current["income"] - prev["income"]
        result["spending_delta"] = current["spending"] - prev["spending"]
        result["savings_delta"] = current["savings"] - prev["savings"]
        result["income_delta_display"] = _format_delta(result["income_delta"])
        result["spending_delta_display"] = _format_delta(result["spending_delta"])
        result["savings_delta_display"] = _format_delta(result["savings_delta"])

    return result


def _savings_goal_periods(base_qs, user, today=None):
    """W / M / 3M net savings vs. sum of the user's goal targets."""
    periods = period_savings(today=today, base_qs=base_qs)
    target = (
        Goal.objects.filter(owner=user).aggregate(s=Sum("target_amount"))["s"]
        or Decimal(0)
    )

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


def _savings_over_time(base_qs, today=None):
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
    qs = base_qs.operational()
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


@login_required
def home(request):
    space = current_space(request.user)
    base_qs = space.transactions_qs() if space else Transaction.objects.none()

    recent = (
        base_qs.select_related("account")
        .order_by("-date", "-created_at")[:3]
    )
    savings_total = base_qs.aggregate(s=Sum("amount"))["s"] or Decimal(0)
    goals = Goal.objects.filter(owner=request.user)
    goal_rows = [
        {
            "goal": g,
            "saved": g.saved_amount(savings_total),
        }
        for g in goals
    ]
    accounts_qs = space.accounts.all() if space else Account.objects.none()
    return render(request, 'dashboard/home.html', {
        'active_tab': 'home',
        'space': space,
        'month_summary': _month_summary(base_qs),
        'savings_goal_periods': _savings_goal_periods(base_qs, request.user),
        'savings_series': _savings_over_time(base_qs),
        'goal_rows': goal_rows,
        'recent_transactions': recent,
        'accounts': accounts_qs,
    })


@login_required
def accounts(request):
    space = current_space(request.user)
    accounts_qs = space.accounts.all() if space else Account.objects.none()
    return render(request, 'dashboard/accounts.html', {
        'active_tab': 'accounts',
        'space': space,
        'accounts': accounts_qs,
    })


@login_required
def account_detail(request, account_id):
    # Scope by owner — only the account owner can see the detail page.
    # Spaces are *views*; mutability and detail-level visibility stay with
    # the user who linked the account (per docs/security-plan.md).
    account = get_object_or_404(Account, pk=account_id, owner=request.user)
    return render(request, 'dashboard/account_detail.html', {
        'active_tab': 'accounts',
        'account': account,
        'transactions': account.transactions.all(),
    })


@login_required
def settings_view(request):
    return render(request, 'dashboard/settings.html', {
        'active_tab': None,
    })
