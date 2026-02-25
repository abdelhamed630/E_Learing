"""
Custom Permissions مشتركة
"""
from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    التحقق من أن المستخدم هو المالك
    يتطلب أن يكون في الـ object حقل 'user'
    """
    message = 'يجب أن تكون مالك هذا العنصر'

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    المالك يمكنه التعديل، الباقي قراءة فقط
    """
    message = 'يمكنك القراءة فقط'

    def has_object_permission(self, request, view, obj):
        # قراءة مسموحة للجميع
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # التعديل للمالك فقط
        return obj.user == request.user


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    الإدمن يمكنه التعديل، الباقي قراءة فقط
    """
    message = 'صلاحيات الإدمن فقط'

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


class IsVerifiedUser(permissions.BasePermission):
    """
    التحقق من أن المستخدم موثق
    """
    message = 'يجب توثيق حسابك أولاً'

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_verified
