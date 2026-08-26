from django.contrib import admin
from core.models import Wedding, WeddingMembership


class MembershipInline(admin.TabularInline):
    model = WeddingMembership
    extra = 0


@admin.register(Wedding)
class WeddingAdmin(admin.ModelAdmin):
    list_display = ['groom_name', 'bride_name', 'wedding_date', 'invite_code', 'total_budget']
    search_fields = ['groom_name', 'bride_name', 'invite_code']
    inlines = [MembershipInline]


@admin.register(WeddingMembership)
class WeddingMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'wedding', 'role', 'joined_at']
    list_filter = ['role']
