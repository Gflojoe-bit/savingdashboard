from itertools import groupby

from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import TransactionForm
from .models import Transaction


def list_view(request):
    qs = Transaction.objects.select_related("account").all()
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


def new(request):
    if request.method == "POST":
        form = TransactionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse("transactions:list"))
    else:
        form = TransactionForm()
    return render(request, "transactions/new.html", {
        "active_tab": "transactions",
        "form": form,
    })
