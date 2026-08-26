"""Core URL patterns."""
from django.urls import path
from core import views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('guide/', views.guide_view, name='guide'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('join/', views.join_workspace_view, name='join_workspace'),
    path('settings/', views.settings_view, name='settings'),
]
