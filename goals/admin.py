from django.contrib import admin

from .models import Goal


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "target_amount", "target_date", "basket_percent")
    list_filter = ("category",)
    search_fields = ("name",)
