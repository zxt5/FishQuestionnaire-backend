from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsSelfOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Get option head
        if request.method in SAFE_METHODS:
            return True
        return obj == request.user
