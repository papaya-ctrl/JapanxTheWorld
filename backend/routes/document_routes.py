from django.urls import path
from controllers.document_controller import health_check, analyze_document
from controllers.checklist_controller import checklist_list_create, checklist_detail_update_delete
from controllers.guide_controller import guide_list, guide_detail
from controllers.resource_controller import resource_list
from controllers.auth_controller import register_user, login_user, logout_user, current_user

urlpatterns = [
    path('health', health_check, name='health_check'),
    path('documents/analyze', analyze_document, name='analyze_document'),
    path('checklist', checklist_list_create, name='checklist_list_create'),
    path('checklist/<int:pk>', checklist_detail_update_delete, name='checklist_detail_update_delete'),
    path('guides', guide_list, name='guide_list'),
    path('guides/<str:guide_id>', guide_detail, name='guide_detail'),
    path('resources', resource_list, name='resource_list'),
    path('auth/register', register_user, name='register_user'),
    path('auth/login', login_user, name='login_user'),
    path('auth/logout', logout_user, name='logout_user'),
    path('auth/me', current_user, name='current_user'),
]
