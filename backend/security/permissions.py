from django.conf import settings
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import BasePermission


class DocumentAccess(BasePermission):
    def has_permission(self, request, view):
        if not getattr(settings, 'DOCUMENT_REQUIRE_AUTH', True):
            return True
        if not request.user or not request.user.is_authenticated:
            raise NotAuthenticated()
        return request.user.has_perm('models.analyze_document')


class ChecklistAccess(BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            return True
        if getattr(settings, 'ALLOW_ANONYMOUS_CHECKLIST', False):
            return True
        raise NotAuthenticated()
