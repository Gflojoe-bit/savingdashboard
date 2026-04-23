from django.db import models


class Account(models.Model):
    CHECKING = "checking"
    SAVINGS = "savings"
    TYPE_CHOICES = [
        (CHECKING, "Checking"),
        (SAVINGS, "Savings"),
    ]

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=CHECKING)
    institution = models.CharField(max_length=100, blank=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return self.name

    @property
    def current_balance(self):
        from django.db.models import Sum

        delta = self.transactions.aggregate(total=Sum("amount"))["total"] or 0
        return self.balance + delta
