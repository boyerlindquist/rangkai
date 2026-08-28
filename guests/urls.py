"""Guest URL patterns."""
from django.urls import path
from guests import views

app_name = 'guests'

urlpatterns = [
    path('', views.guest_list, name='list'),
    path('add/', views.add_guest, name='add'),
    path('bulk-add/', views.bulk_add_guests, name='bulk_add'),
    path('import/', views.import_guests, name='import'),
    path('template/download/', views.download_guest_template, name='download_template'),
    path('<int:pk>/update/', views.update_guest, name='update'),
    path('<int:pk>/delete/', views.delete_guest, name='delete'),
    path('<int:pk>/toggle-rsvp/', views.toggle_rsvp, name='toggle_rsvp'),
    path('catering-config/', views.update_catering_config, name='catering_config'),
]
