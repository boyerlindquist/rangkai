from django.contrib import admin
from core.models import AccountProfile, Wedding, WeddingMembership, WorkspaceInvitation, Order


class MembershipInline(admin.TabularInline):
    model = WeddingMembership
    extra = 0


class InvitationInline(admin.TabularInline):
    model = WorkspaceInvitation
    extra = 0


@admin.register(AccountProfile)
class AccountProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'account_type', 'organization_name', 'project_quota', 'plan_status']
    list_filter = ['account_type', 'plan_status']
    search_fields = ['user__username', 'user__email', 'organization_name']


@admin.register(Wedding)
class WeddingAdmin(admin.ModelAdmin):
    list_display = ['groom_name', 'bride_name', 'wedding_date', 'managed_by', 'allow_wo_budget_access', 'status', 'invite_code']
    list_filter = ['status', 'allow_wo_budget_access']
    search_fields = ['groom_name', 'bride_name', 'invite_code']
    inlines = [MembershipInline, InvitationInline]


@admin.register(WeddingMembership)
class WeddingMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'wedding', 'role', 'joined_at']
    list_filter = ['role']


@admin.register(WorkspaceInvitation)
class WorkspaceInvitationAdmin(admin.ModelAdmin):
    list_display = ['code', 'wedding', 'role', 'uses_count', 'max_uses', 'is_active', 'created_at']
    list_filter = ['role', 'is_active']
    search_fields = ['code', 'wedding__groom_name', 'wedding__bride_name']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_code', 'user', 'plan_type', 'amount', 'payment_method', 'status', 'created_at']
    list_filter = ['plan_type', 'status', 'payment_method']
    search_fields = ['order_code', 'user__username', 'customer_email']
