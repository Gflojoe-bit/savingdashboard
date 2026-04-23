from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "account", "amount", "description", "merchant", "pending")
    list_filter = ("account", "pending", "category")
    search_fields = ("description", "merchant", "external_id")
    date_hierarchy = "date"
