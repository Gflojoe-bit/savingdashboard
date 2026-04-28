from django.contrib import admin

from .models import Space, SpaceMembership


@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "is_personal", "created_at")
    list_filter = ("is_personal",)
    search_fields = ("name", "owner__username")
    filter_horizontal = ("accounts",)


@admin.register(SpaceMembership)
class SpaceMembershipAdmin(admin.ModelAdmin):
    list_display = ("space", "user", "joined_at")
    search_fields = ("space__name", "user__username")
