from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsSelfOrReadOnly(BasePermission):
    message = '仅创建者可以编辑'

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.user == request.user