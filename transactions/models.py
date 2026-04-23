from django.db import models

from accounts.models import Account


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
