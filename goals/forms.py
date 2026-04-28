from decimal import Decimal

from django import forms
from django.db.models import Sum
from django.forms import modelformset_factory

from .models import Goal


class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ["name", "category", "target_amount", "target_date", "basket_percent"]
        widgets = {
            "target_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        # `user` scopes the basket-total check to the saver's own goals;
        # other users' baskets are independent.
        super().__init__(*args, **kwargs)
        self._user = user

    def clean(self):
        cleaned = super().clean()
        new_pct = cleaned.get("basket_percent")
        if new_pct is None:
            return cleaned

        others = Goal.objects.all()
        if self._user is not None:
            others = others.filter(owner=self._user)
        if self.instance.pk:
            others = others.exclude(pk=self.instance.pk)
        existing = others.aggregate(s=Sum("basket_percent"))["s"] or Decimal(0)
        total = existing + new_pct
        if total != Decimal(100):
            available = Decimal(100) - existing
            raise forms.ValidationError(
                f"Basket must total 100%. Existing goals use {existing}%, "
                f"so this goal needs to be {available}%. "
                f"Edit the basket first if you need to make room."
            )
        return cleaned


class BasketAllocationForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ["basket_percent"]


BasketFormSet = modelformset_factory(
    Goal,
    form=BasketAllocationForm,
    extra=0,
    can_delete=False,
)


def basket_total(formset):
    total = Decimal(0)
    for form in formset.forms:
        pct = form.cleaned_data.get("basket_percent") if form.is_bound else form.initial.get("basket_percent")
        if pct is not None:
            total += Decimal(pct)
    return total
