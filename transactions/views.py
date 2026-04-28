from itertools import groupby

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from auth_app.models import current_space

from .forms import TransactionForm
from .models import Transaction


@login_required
def list_view(request):
    space = current_space(request.user)
    qs = (
        space.transactions_qs().select_related("account")
        if space
        else Transaction.objects.none()
    )
    months = [
        {
            "label": key.strftime("%B %Y"),
            "transactions": list(items),
        }
        for key, items in groupby(qs, key=lambda t: t.date.replace(day=1))
    ]
    return render(request, "transactions/list.html", {
        "active_tab": "transactions",
        "months": months,
    })


@login_required
def new(request):
    if request.method == "POST":
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            return redirect(reverse("transactions:list"))
    else:
        form = TransactionForm(user=request.user)
    return render(request, "transactions/new.html", {
        "active_tab": "transactions",
        "form": form,
    })
