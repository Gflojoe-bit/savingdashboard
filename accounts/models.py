from decimal import ROUND_HALF_UP, Decimal

from django.db import models


CENTS = Decimal("0.01")


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
    external_id = models.CharField(max_length=64, blank=True, null=True, unique=True)

    def __str__(self):
        return self.name

    @property
    def current_balance(self):
        from django.db.models import Sum

        delta = self.transactions.aggregate(total=Sum("amount"))["total"] or Decimal(0)
        # SQLite's SUM() on DecimalField returns raw precision (e.g. 9284.6300000000),
        # so quantize back to cents before display.
        return (self.balance + delta).quantize(CENTS, rounding=ROUND_HALF_UP)
