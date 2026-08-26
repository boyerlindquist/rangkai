from django.contrib import admin
from operations.models import TaskMilestone, RundownEvent, AssetCustodian, FabricEntry


@admin.register(TaskMilestone)
class TaskMilestoneAdmin(admin.ModelAdmin):
    list_display = ['title', 'phase', 'assignee', 'status', 'is_critical']
    list_filter = ['phase', 'status', 'assignee']


@admin.register(RundownEvent)
class RundownEventAdmin(admin.ModelAdmin):
    list_display = ['activity', 'start_time', 'end_time', 'pic', 'location']


@admin.register(AssetCustodian)
class AssetCustodianAdmin(admin.ModelAdmin):
    list_display = ['name', 'asset_category', 'pic_name', 'status']
    list_filter = ['asset_category', 'status']


@admin.register(FabricEntry)
class FabricEntryAdmin(admin.ModelAdmin):
    list_display = ['recipient_name', 'gender', 'garment_type', 'size_category']
    list_filter = ['gender', 'garment_type']
