from django.contrib import admin
from finances.models import BudgetCategory, BudgetItem, ContributionShare


@admin.register(BudgetCategory)
class BudgetCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'wedding', 'allocation_percentage']
    list_filter = ['wedding']


@admin.register(BudgetItem)
class BudgetItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'actual_cost', 'paid_amount', 'payment_status', 'due_date']
    list_filter = ['payment_status', 'payer']


@admin.register(ContributionShare)
class ContributionShareAdmin(admin.ModelAdmin):
    list_display = ['wedding', 'contributor', 'percentage', 'fixed_amount']
