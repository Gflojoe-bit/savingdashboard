from datetime import date, timedelta
from decimal import Decimal

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Goal(models.Model):
    EMERGENCY = "emergency"
    INVESTING = "investing"
    VACATION = "vacation"
    HOME = "home"
    OTHER = "other"
    CATEGORY_CHOICES = [
        (EMERGENCY, "Emergency fund"),
        (INVESTING, "Investing"),
        (VACATION, "Vacation"),
        (HOME, "Home"),
        (OTHER, "Other"),
    ]

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=OTHER)
    target_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    target_date = models.DateField(blank=True, null=True)
    basket_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Share of each deposit allocated to this goal (0–100).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def saved_amount(self, savings_total):
        """Lazy progress: portion of period savings allocated by basket."""
        return (Decimal(savings_total) * self.basket_percent) / Decimal(100)

    def progress_pct(self, savings_total):
        if self.target_amount <= 0:
            return 0
        saved = self.saved_amount(savings_total)
        pct = (saved / self.target_amount) * Decimal(100)
        return max(0, min(100, int(round(pct))))


def net_savings(qs=None):
    """Net savings across a Transaction queryset (income − spending), floored at 0.

    Negative cash flow in a period contributes nothing to goals — you can't
    distribute negative savings. The income/spending/savings math itself is
    defined in `transactions.models.TransactionQuerySet.summary()`; the
    floor-at-0 rule is the goals-specific policy applied here.
    """
    from transactions.models import Transaction

    qs = Transaction.objects.all() if qs is None else qs
    return max(Decimal(0), qs.summary()["savings"])


def period_savings(today=None):
    """Net savings (floored at 0) for week / month / year to date, plus all-time."""
    from transactions.models import Transaction

    today = today or date.today()
    starts = {
        "week": today - timedelta(days=today.weekday()),
        "month": today.replace(day=1),
        "year": today.replace(month=1, day=1),
    }
    result = {
        key: net_savings(Transaction.objects.in_range(start, today))
        for key, start in starts.items()
    }
    result["all"] = net_savings()
    return result
