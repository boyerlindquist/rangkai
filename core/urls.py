"""Core URL patterns."""
from django.urls import path
from core import views

app_name = 'core'

urlpatterns = [
    path('', views.home_view, name='dashboard'),
    path('landing/', views.landing_view, name='landing'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('dashboard/', views.dashboard_view, name='dashboard_alias'),
    path('guide/', views.guide_view, name='guide'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('join/', views.join_workspace_view, name='join_workspace'),

    # Multi-workspace switcher
    path('switch-workspace/<int:pk>/', views.switch_workspace_view, name='switch_workspace'),
    path('switch-workspace/exit/', views.exit_workspace_inspect_view, name='exit_workspace'),

    # WO Portal (WO Manager & Admin)
    path('wo/', views.wo_portal_view, name='wo_portal'),
    path('wo/create-project/', views.wo_create_project_view, name='wo_create_project'),

    # Platform Admin Console (ALL access)
    path('platform-admin/', views.admin_console_view, name='admin_console'),

    # Workspace Settings & Role-Bound Invitations
    path('settings/', views.settings_view, name='settings'),
    path('settings/regenerate-code/', views.regenerate_invite_code_view, name='regenerate_invite_code'),
    path('settings/invitations/create/', views.create_invitation_view, name='create_invitation'),
    path('settings/invitations/<int:pk>/revoke/', views.revoke_invitation_view, name='revoke_invitation'),
    path('settings/wo-privacy/', views.toggle_wo_privacy_view, name='toggle_wo_privacy'),
    path('settings/member/<int:pk>/', views.manage_member_view, name='manage_member'),
]
