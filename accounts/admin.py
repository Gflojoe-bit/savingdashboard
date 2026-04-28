from django.contrib import admin

from .models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "type", "institution", "balance")
    list_filter = ("type", "owner")
    search_fields = ("name", "institution", "owner__username")
