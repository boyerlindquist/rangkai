from django.contrib import admin
from vendors.models import VendorCandidate


@admin.register(VendorCandidate)
class VendorCandidateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price_estimate', 'weighted_total_score', 'status']
    list_filter = ['category', 'status']
    search_fields = ['name']
