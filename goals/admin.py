from django.contrib import admin

from .models import Goal


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "category", "target_amount", "target_date", "basket_percent")
    list_filter = ("category", "owner")
    search_fields = ("name", "owner__username")
