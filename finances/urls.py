"""Finance URL patterns."""
from django.urls import path
from finances import views

app_name = 'finances'

urlpatterns = [
    path('', views.budget_dashboard, name='dashboard'),
    path('add/', views.add_budget_item, name='add_item'),
    path('<int:pk>/update/', views.update_budget_item, name='update_item'),
    path('<int:pk>/delete/', views.delete_budget_item, name='delete_item'),
    path('<int:pk>/toggle-status/', views.toggle_payment_status, name='toggle_status'),
    path('category/config/', views.config_allocations, name='config_allocations'),
    path('category/<int:pk>/update/', views.update_budget_category, name='update_category'),
    
    # Savings Tracker
    path('savings/', views.savings_tracker_view, name='savings_tracker'),
    path('savings/update-goal/', views.update_savings_goal, name='update_savings_goal'),
    path('savings/add-deposit/', views.add_savings_deposit, name='add_savings_deposit'),
]
