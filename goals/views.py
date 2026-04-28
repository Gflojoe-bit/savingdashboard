from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from auth_app.models import current_space
from transactions.models import Transaction

from .forms import BasketFormSet, GoalForm
from .models import Goal, net_savings, period_savings


def _user_base_qs(user):
    """Transactions in the user's current Space — scope for savings math."""
    space = current_space(user)
    return space.transactions_qs() if space else Transaction.objects.none()


def _attach_progress(goals, savings):
    rows = []
    for goal in goals:
        saved = goal.saved_amount(savings)
        rows.append({
            "goal": goal,
            "saved": saved,
            "pct": goal.progress_pct(savings),
            "remaining": max(Decimal(0), goal.target_amount - saved),
        })
    return rows


@login_required
def list_view(request):
    goals = Goal.objects.filter(owner=request.user)
    savings = net_savings(_user_base_qs(request.user))
    basket_total = sum((g.basket_percent for g in goals), Decimal(0))
    return render(request, "goals/list.html", {
        "active_tab": "goals",
        "rows": _attach_progress(goals, savings),
        "savings": savings,
        "basket_total": basket_total,
        "basket_balanced": basket_total == Decimal(100),
    })


@login_required
def detail(request, goal_id):
    goal = get_object_or_404(Goal, pk=goal_id, owner=request.user)
    periods = period_savings(base_qs=_user_base_qs(request.user))
    period_rows = [
        {
            "key": key,
            "label": label,
            "saved": goal.saved_amount(periods[key]),
        }
        for key, label in [("week", "Past week"), ("month", "Past month"), ("three_months", "Past 3 months")]
    ]
    saved_all = goal.saved_amount(periods["all"])
    return render(request, "goals/detail.html", {
        "active_tab": "goals",
        "goal": goal,
        "saved": saved_all,
        "pct": goal.progress_pct(periods["all"]),
        "remaining": max(Decimal(0), goal.target_amount - saved_all),
        "period_rows": period_rows,
    })


@login_required
def new(request):
    if request.method == "POST":
        form = GoalForm(request.POST, user=request.user)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.owner = request.user
            goal.save()
            return redirect(reverse("goals:list"))
    else:
        form = GoalForm(user=request.user)

    from django.db.models import Sum
    existing = (
        Goal.objects.filter(owner=request.user).aggregate(s=Sum("basket_percent"))["s"]
        or Decimal(0)
    )
    available = Decimal(100) - existing

    return render(request, "goals/new.html", {
        "active_tab": "goals",
        "form": form,
        "existing_pct": existing,
        "available_pct": available,
    })


@login_required
def basket(request):
    qs = Goal.objects.filter(owner=request.user)
    if request.method == "POST":
        formset = BasketFormSet(request.POST, queryset=qs)
        if formset.is_valid():
            total = sum(
                (f.cleaned_data.get("basket_percent") or Decimal(0)) for f in formset.forms
            )
            if total != Decimal(100) and qs.exists():
                messages.error(request, f"Basket percentages must total 100%. Currently {total}%.")
            else:
                formset.save()
                messages.success(request, "Basket updated.")
                return redirect(reverse("goals:list"))
    else:
        formset = BasketFormSet(queryset=qs)

    return render(request, "goals/basket.html", {
        "active_tab": "goals",
        "formset": formset,
    })
