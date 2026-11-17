"""Operations URL patterns — Checklist route (/checklist/)."""
from django.urls import path
from operations import views

app_name = 'operations'

urlpatterns = [
    path('', views.checklist_view, name='checklist'),
    path('task/add/', views.add_task, name='add_task'),
    path('task/add-guide/', views.add_guide_task, name='add_guide_task'),
    path('task/<int:pk>/update/', views.update_task, name='update_task'),
    path('task/<int:pk>/toggle/', views.toggle_task_status, name='toggle_task'),
    path('task/<int:pk>/delete/', views.delete_task, name='delete_task'),

    # Phase Customization & Redesign (Inline + Bulk + Safe Delete + Reset/Preset)
    path('phase/add/', views.add_phase, name='add_phase'),
    path('phase/bulk/', views.bulk_manage_phases, name='bulk_manage_phases'),
    path('phase/reset/', views.reset_or_apply_preset, name='reset_or_apply_preset'),
    path('phase/<str:phase_key>/update/', views.update_phase, name='update_phase'),
    path('phase/<str:phase_key>/delete/', views.delete_phase, name='delete_phase'),
    
    # Detailed Checklists
    path('details/', views.detail_checklists_view, name='detail_checklists'),
    path('details/doc/add/', views.add_document, name='add_document'),
    path('details/doc/<int:pk>/toggle/', views.toggle_document_status, name='toggle_document'),
    path('details/doc/<int:pk>/update/', views.update_document, name='update_document'),
    path('details/doc/<int:pk>/delete/', views.delete_document, name='delete_document'),
    path('details/seserahan/add/', views.add_seserahan, name='add_seserahan'),
    path('details/seserahan/<int:pk>/toggle/', views.toggle_seserahan_status, name='toggle_seserahan'),
    path('details/seserahan/<int:pk>/update/', views.update_seserahan, name='update_seserahan'),
    path('details/seserahan/<int:pk>/delete/', views.delete_seserahan, name='delete_seserahan'),
]
