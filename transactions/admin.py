from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "account",
        "amount",
        "description",
        "merchant",
        "pending",
        "is_savings_transfer",
    )
    list_filter = ("account", "pending", "is_savings_transfer", "category")
    search_fields = ("description", "merchant", "external_id")
    date_hierarchy = "date"
