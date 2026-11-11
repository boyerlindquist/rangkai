"""Operations URL patterns — Operations Hub route (/operations/)."""
from django.urls import path
from operations import views

app_name = 'operations'

urlpatterns = [
    path('', views.operations_hub, name='operations_hub'),
    path('rundown/add/', views.add_rundown_event, name='add_rundown'),
    path('rundown/<int:pk>/update/', views.update_rundown_event, name='update_rundown'),
    path('rundown/<int:pk>/delete/', views.delete_rundown_event, name='delete_rundown'),
    path('asset/add/', views.add_asset, name='add_asset'),
    path('asset/<int:pk>/update/', views.update_asset, name='update_asset'),
    path('asset/<int:pk>/delete/', views.delete_asset, name='delete_asset'),
    path('asset/<int:pk>/toggle/', views.toggle_asset_status, name='toggle_asset'),
    path('fabric/add/', views.add_fabric_entry, name='add_fabric'),
    path('fabric/<int:pk>/update/', views.update_fabric_entry, name='update_fabric'),
    path('fabric/<int:pk>/delete/', views.delete_fabric_entry, name='delete_fabric'),
]
