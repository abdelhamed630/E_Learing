"""
Admin للتسجيلات
"""
from django.contrib import admin
from .models import (
    Enrollment, VideoProgress, CourseNote,
    Certificate, LearningStreak
)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'course', 'status', 'progress',
        'certificate_issued', 'enrolled_at', 'completed_at'
    ]
    list_filter = ['status', 'certificate_issued', 'enrolled_at']
    search_fields = [
        'student__user__username',
        'student__user__email',
        'course__title'
    ]
    readonly_fields = [
        'enrolled_at', 'started_at', 'completed_at', 'last_accessed'
    ]
    
    fieldsets = (
        ('معلومات التسجيل', {
            'fields': ('student', 'course', 'status')
        }),
        ('التقدم', {
            'fields': ('progress', 'total_time_spent')
        }),
        ('الشهادة', {
            'fields': ('certificate_issued', 'certificate_url')
        }),
        ('التواريخ', {
            'fields': (
                'enrolled_at', 'started_at', 'completed_at',
                'expires_at', 'last_accessed'
            ),
            'classes': ('collapse',)
        }),
    )


@admin.register(VideoProgress)
class VideoProgressAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'video', 'completion_percentage',
        'completed', 'view_count', 'last_watched'
    ]
    list_filter = ['completed', 'last_watched']
    search_fields = [
        'student__user__username',
        'video__title',
        'video__course__title'
    ]
    readonly_fields = ['first_watched', 'last_watched', 'completed_at']
    
    def completion_percentage(self, obj):
        return f"{obj.completion_percentage}%"
    completion_percentage.short_description = 'نسبة الإنجاز'


@admin.register(CourseNote)
class CourseNoteAdmin(admin.ModelAdmin):
    list_display = ['student', 'title', 'video', 'created_at']
    list_filter = ['created_at']
    search_fields = [
        'student__user__username',
        'title',
        'content',
        'enrollment__course__title'
    ]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = [
        'certificate_number', 'get_student', 'get_course',
        'final_grade', 'issued_at'
    ]
    list_filter = ['issued_at']
    search_fields = [
        'certificate_number',
        'enrollment__student__user__username',
        'enrollment__course__title'
    ]
    readonly_fields = ['issued_at']
    
    def get_student(self, obj):
        return obj.enrollment.student.user.username
    get_student.short_description = 'الطالب'
    
    def get_course(self, obj):
        return obj.enrollment.course.title
    get_course.short_description = 'الكورس'


@admin.register(LearningStreak)
class LearningStreakAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'date', 'time_spent',
        'videos_watched', 'notes_added'
    ]
    list_filter = ['date']
    search_fields = ['student__user__username']
    readonly_fields = ['created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
