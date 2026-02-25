"""
Permissions للامتحانات
"""
from rest_framework import permissions
from enrollments.models import Enrollment
from .models import ExamAttempt


class IsEnrolledInCourse(permissions.BasePermission):
    """التحقق من تسجيل الطالب في الكورس"""
    message = 'يجب أن تكون مسجلاً في الكورس للوصول للامتحان'

    def has_object_permission(self, request, view, obj):
        if not hasattr(request.user, 'student_profile'):
            return False
        student = request.user.student_profile
        course = obj.course if hasattr(obj, 'course') else obj.exam.course
        return Enrollment.objects.filter(
            student=student,
            course=course,
            status='active'
        ).exists()


class HasAttemptsLeft(permissions.BasePermission):
    """التحقق من وجود محاولات متبقية"""
    message = 'لقد استنفدت جميع محاولاتك لهذا الامتحان'

    def has_object_permission(self, request, view, obj):
        if not hasattr(request.user, 'student_profile'):
            return False
        student = request.user.student_profile
        attempts_used = ExamAttempt.objects.filter(
            student=student,
            exam=obj
        ).exclude(status='in_progress').count()
        return attempts_used < obj.max_attempts


class IsAttemptOwner(permissions.BasePermission):
    """التحقق من أن المحاولة تخص الطالب"""
    message = 'هذه المحاولة لا تخصك'

    def has_object_permission(self, request, view, obj):
        if not hasattr(request.user, 'student_profile'):
            return False
        return obj.student == request.user.student_profile


class IsAttemptInProgress(permissions.BasePermission):
    """التحقق من أن المحاولة لا تزال جارية"""
    message = 'هذه المحاولة ليست جارية'

    def has_object_permission(self, request, view, obj):
        if obj.is_expired:
            # انتهت المدة - تسليم تلقائي
            from exams.tasks import auto_submit_attempt
            auto_submit_attempt.delay(obj.id)
            return False
        return obj.status == 'in_progress'
