"""
الصلاحيات لتطبيق الطلاب
"""
from rest_framework import permissions


class IsStudent(permissions.BasePermission):
    """
    صلاحية: السماح فقط للطلاب
    الطالب يجب أن يكون لديه student_profile
    """
    message = 'فقط الطلاب يمكنهم الوصول لهذا المورد'
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'student_profile')
        )


class IsStudentOwner(permissions.BasePermission):
    """
    صلاحية: السماح للطالب بالوصول لبياناته فقط
    """
    message = 'يمكنك الوصول لبياناتك الشخصية فقط'
    
    def has_object_permission(self, request, view, obj):
        # التحقق من أن الكائن هو الطالب نفسه
        return obj.user == request.user


class IsActiveStudent(permissions.BasePermission):
    """
    صلاحية: السماح فقط للطلاب النشطين
    """
    message = 'حسابك غير نشط. الرجاء التواصل مع الإدارة'
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'student_profile') and
            request.user.student_profile.is_active
        )


class CanViewCourses(permissions.BasePermission):
    """
    صلاحية: الطالب يمكنه مشاهدة الكورسات والفيديوهات
    """
    message = 'ليس لديك صلاحية لمشاهدة هذا المحتوى'
    
    def has_permission(self, request, view):
        # الطلاب يمكنهم القراءة فقط
        if request.method in permissions.SAFE_METHODS:
            return (
                request.user and 
                request.user.is_authenticated and 
                hasattr(request.user, 'student_profile')
            )
        return False


class CanTakeExams(permissions.BasePermission):
    """
    صلاحية: الطالب يمكنه حل الامتحانات فقط
    """
    message = 'ليس لديك صلاحية لأداء الامتحانات'
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'student_profile') and
            request.user.student_profile.is_active
        )
