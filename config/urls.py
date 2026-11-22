"""
Root URL Configuration for Smart Wedding Engine.
"""
from django.contrib import admin
from django.urls import path, include
from operations import views as operations_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('calendar/', operations_views.calendar_view, name='calendar'),
    path('notes/', operations_views.notes_view, name='notes'),
    path('notes/create/', operations_views.note_create_api, name='note_create'),
    path('notes/<int:pk>/save/', operations_views.note_save_api, name='note_save'),
    path('notes/<int:pk>/delete/', operations_views.note_delete_api, name='note_delete'),
    path('notes/toggle-all-visibility/', operations_views.notes_toggle_all_visibility_api, name='notes_toggle_all_visibility'),
    path('budgets/', include('finances.urls')),
    path('guests/', include('guests.urls')),
    path('vendors/', include('vendors.urls')),
    path('checklist/', include(('operations.urls', 'operations'), namespace='operations-checklist')),
    path('operations/', include(('operations.urls_ops', 'operations'), namespace='operations-hub')),
]
