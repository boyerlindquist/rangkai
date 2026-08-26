"""Vendor URL patterns."""
from django.urls import path
from vendors import views

app_name = 'vendors'

urlpatterns = [
    path('', views.vendor_compare, name='compare'),
    path('add/', views.add_vendor, name='add'),
    path('<int:pk>/update/', views.update_vendor, name='update'),
    path('<int:pk>/delete/', views.delete_vendor, name='delete'),
    path('<int:pk>/toggle-status/', views.update_vendor_status, name='toggle_status'),
]
