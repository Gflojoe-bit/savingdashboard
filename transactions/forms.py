from django import forms

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
