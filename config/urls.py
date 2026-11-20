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
    path('budgets/', include('finances.urls')),
    path('guests/', include('guests.urls')),
    path('vendors/', include('vendors.urls')),
    path('checklist/', include(('operations.urls', 'operations'), namespace='operations-checklist')),
    path('operations/', include(('operations.urls_ops', 'operations'), namespace='operations-hub')),
]
