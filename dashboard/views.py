"""Dashboard aggregation views.

Accounts/transactions/goals detail lives in their own apps. This layer composes
them for the home screen and the accounts/goals landing pages.
"""

from datetime import date

from django.db.models import Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from accounts.models import Account
from transactions.models import Transaction

from . import fake_data


def _month_summary(today=None):
    today = today or date.today()
    month_qs = Transaction.objects.filter(date__year=today.year, date__month=today.month)
    income = month_qs.filter(amount__gt=0).aggregate(s=Sum("amount"))["s"] or 0
    spending = month_qs.filter(amount__lt=0).aggregate(s=Sum("amount"))["s"] or 0
    spending = -spending  # flip sign for display
    return {
        "label": today.strftime("%B %Y"),
        "income": income,
        "spending": spending,
        "savings": income - spending,
    }


def home(request):
    recent = (
        Transaction.objects.select_related("account")
        .order_by("-date", "-created_at")[:3]
    )
    return render(request, 'dashboard/home.html', {
        'active_tab': 'home',
        'month_summary': _month_summary(),
        'savings_goal_periods': fake_data.SAVINGS_GOAL_PERIODS,
        'goals': fake_data.GOALS,
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


def goals(request):
    return render(request, 'dashboard/goals.html', {
        'active_tab': 'goals',
        'goals': fake_data.GOALS,
    })


def goal_detail(request, goal_id):
    goal = next((g for g in fake_data.GOALS if g['id'] == goal_id), None)
    if goal is None:
        raise Http404("Goal not found")
    return render(request, 'dashboard/goal_detail.html', {
        'active_tab': 'goals',
        'goal': goal,
    })


def settings_view(request):
    return render(request, 'dashboard/settings.html', {
        'active_tab': None,
    })
