from django import forms

from accounts.models import Account

from .models import Transaction


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["account", "date", "amount", "description", "is_savings_transfer"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {
            "is_savings_transfer": "Transfer between my accounts (exclude from spending)",
        }

    def __init__(self, *args, user=None, **kwargs):
        # Scope the account dropdown to the user's own accounts. Per
        # docs/security-plan.md, only the account owner can mutate it —
        # no posting transactions onto a Space co-member's account even
        # if it's opted into the same Space.
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["account"].queryset = Account.objects.filter(owner=user)
