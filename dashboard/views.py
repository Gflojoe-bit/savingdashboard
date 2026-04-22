"""UI scaffold views — hardcoded data.

Every view here renders against placeholder data from ``fake_data`` so the
full clickable app exists before the real models (accounts / transactions /
goals) are built. As each subsystem branch lands, its view moves to the
owning app and the fake_data reference gets swapped for a queryset.
"""

from django.http import Http404
from django.shortcuts import render

from . import fake_data


def home(request):
    return render(request, 'dashboard/home.html', {
        'active_tab': 'home',
        'total_savings': fake_data.TOTAL_SAVINGS,
        'goals': fake_data.GOALS,
        'recent_transactions': fake_data.RECENT_TRANSACTIONS,
        'accounts': fake_data.ACCOUNTS,
    })


def accounts(request):
    return render(request, 'dashboard/accounts.html', {
        'active_tab': 'accounts',
        'accounts': fake_data.ACCOUNTS,
    })


def account_detail(request, account_id):
    account = next((a for a in fake_data.ACCOUNTS if a['id'] == account_id), None)
    if account is None:
        raise Http404("Account not found")
    return render(request, 'dashboard/account_detail.html', {
        'active_tab': 'accounts',
        'account': account,
        'transactions': fake_data.TRANSACTIONS_BY_ACCOUNT.get(account_id, []),
    })


def transactions(request):
    return render(request, 'dashboard/transactions.html', {
        'active_tab': 'transactions',
        'months': fake_data.TRANSACTIONS_BY_MONTH,
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
