from decimal import Decimal

from django.db import models
from django.db.models import Sum

from accounts.models import Account


class TransactionQuerySet(models.QuerySet):
    """Composable primitives for income/spending/savings math.

    Callers chain these instead of reimplementing filters and aggregates
    in each view. Keeping the manager policy-free: it exposes plumbing,
    not rules. Domain rules (e.g. "negative savings floored at 0" for goals)
    live in the caller.
    """

    def in_range(self, start, end):
        """Transactions with `start <= date <= end` (both inclusive)."""
        return self.filter(date__gte=start, date__lte=end)

    def summary(self):
        """Return {'income': Decimal, 'spending': Decimal, 'savings': Decimal}.

        income   = sum of positive amounts in the queryset
        spending = sum of negative amounts in the queryset, sign-flipped for display
        savings  = income - spending
        """
        income = self.filter(amount__gt=0).aggregate(s=Sum("amount"))["s"] or Decimal(0)
        spending_raw = self.filter(amount__lt=0).aggregate(s=Sum("amount"))["s"] or Decimal(0)
        spending = -spending_raw
        return {
            "income": income,
            "spending": spending,
            "savings": income - spending,
        }


class Transaction(models.Model):
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="transactions"
    )
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)

    external_id = models.CharField(max_length=64, blank=True, null=True, unique=True)
    pending = models.BooleanField(default=False)
    merchant = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = TransactionQuerySet.as_manager()

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.date} {self.description or self.merchant} {self.amount}"

    @property
    def is_credit(self):
        return self.amount >= 0

    @property
    def amount_abs(self):
        return abs(self.amount)
