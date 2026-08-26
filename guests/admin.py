from django.contrib import admin
from guests.models import Guest, CateringConfig


@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ['name', 'wedding', 'relation_side', 'category', 'pax_allocation', 'rsvp_status', 'checked_in']
    list_filter = ['relation_side', 'category', 'rsvp_status']
    search_fields = ['name']


@admin.register(CateringConfig)
class CateringConfigAdmin(admin.ModelAdmin):
    list_display = ['wedding', 'attendance_rate', 'crew_count']
